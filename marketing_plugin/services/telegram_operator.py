"""Telegram Operator Service for Marketing OS.

Implements the daily founder control and approval surface (A-013, A-026),
guaranteeing human oversight for external public actions (A-007, I-02),
strict admin allowlist verification, and idempotent approval state transitions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.lead_repo import LeadRepository
from schemas.models import Approval, ApprovalDecision, LeadStatus

logger = logging.getLogger(__name__)


@dataclass
class TelegramOperatorConfig:
    """Configuration for Telegram Operator security and interaction."""
    bot_token: Optional[str] = None
    admin_user_ids: Set[str] = field(default_factory=set)
    admin_chat_ids: Set[str] = field(default_factory=set)
    language: str = "ar"


@dataclass
class CommandResponse:
    """Structured response to a Telegram operator command."""
    text: str
    reply_markup: Optional[Dict[str, Any]] = None
    parse_mode: str = "Markdown"
    success: bool = True
    error: Optional[str] = None


@dataclass
class CallbackResult:
    """Result of handling an interactive button callback."""
    success: bool
    approval_id: str
    decision: str
    actor_id: str
    message_text: str
    alert_text: str
    error: Optional[str] = None


class TelegramOperatorService:
    """Manages Telegram bot command routing, authorization, and interactive approvals."""

    def __init__(
        self,
        db: Optional[Database] = None,
        config: Optional[TelegramOperatorConfig] = None,
    ) -> None:
        self.db = db or Database("data/marketing.db")
        self.config = config or TelegramOperatorConfig()

    def is_authorized(
        self,
        user_id: int | str,
        chat_id: Optional[int | str] = None,
    ) -> bool:
        """Enforces strict admin allowlist verification per A-026."""
        uid = str(user_id).strip()
        if not self.config.admin_user_ids:
            logger.warning("No admin user IDs configured; rejecting access by default.")
            return False

        if uid not in self.config.admin_user_ids:
            logger.warning("Unauthorized operator attempt from user_id=%s", uid)
            return False

        if chat_id is not None and self.config.admin_chat_ids:
            cid = str(chat_id).strip()
            if cid not in self.config.admin_chat_ids:
                logger.warning("Operator user_id=%s from unauthorized chat_id=%s", uid, cid)
                return False

        return True

    def handle_command(
        self,
        command_text: str,
        user_id: int | str,
        chat_id: Optional[int | str] = None,
    ) -> CommandResponse:
        """Parses and executes an authorized operator command."""
        if not self.is_authorized(user_id=user_id, chat_id=chat_id):
            return CommandResponse(
                text="⛔ *عذراً، هذا الحساب غير مصرح له بتشغيل أوامر نظام Marketing OS.*\n"
                     "تم تسجيل محاولة الوصول للتدقيق الأمني بموجب السياسة A-026.",
                success=False,
                error="Unauthorized access",
            )

        cmd_raw = command_text.strip()
        parts = cmd_raw.split()
        if not parts:
            return CommandResponse(text="الرجاء إدخال أمر صالح. اكتب /help لعرض الأوامر.")

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ("/start", "/help"):
            return self._cmd_help()
        elif cmd == "/status":
            return self._cmd_status()
        elif cmd == "/leads":
            return self._cmd_leads(country_code=args[0] if args else None)
        elif cmd == "/pending":
            return self._cmd_pending()
        elif cmd == "/approve" and args:
            return self._cmd_direct_resolve(approval_id=args[0], decision=ApprovalDecision.APPROVED, actor_id=str(user_id))
        elif cmd == "/reject" and args:
            return self._cmd_direct_resolve(approval_id=args[0], decision=ApprovalDecision.REJECTED, actor_id=str(user_id))
        elif cmd == "/intake":
            return self._cmd_intake(args)
        else:
            return CommandResponse(
                text=f"⚠️ أمر غير معروف: `{cmd}`.\nاكتب /help للاطلاع على قائمة الأوامر المتاحة.",
                success=False,
            )

    def handle_callback(
        self,
        callback_data: str,
        user_id: int | str,
        chat_id: Optional[int | str] = None,
        user_name: Optional[str] = None,
    ) -> CallbackResult:
        """Handles interactive inline button callbacks with idempotency and audit tracking (A-026)."""
        uid = str(user_id).strip()
        if not self.is_authorized(user_id=user_id, chat_id=chat_id):
            return CallbackResult(
                success=False,
                approval_id="",
                decision="",
                actor_id=uid,
                message_text="",
                alert_text="⛔ غير مصرح لك بتنفيذ هذا الإجراء (A-026).",
                error="Unauthorized callback execution",
            )

        # Parse callback data: "appr:<approval_id>:<decision>"
        parts = callback_data.split(":")
        if len(parts) != 3 or parts[0] != "appr":
            return CallbackResult(
                success=False,
                approval_id="",
                decision="",
                actor_id=uid,
                message_text="",
                alert_text="تنسيق رد غير صالح.",
                error="Invalid callback data format",
            )

        approval_id = parts[1]
        decision_raw = parts[2].lower()

        try:
            target_decision = ApprovalDecision(decision_raw)
        except ValueError:
            return CallbackResult(
                success=False,
                approval_id=approval_id,
                decision=decision_raw,
                actor_id=uid,
                message_text="",
                alert_text="قرار غير صالح.",
                error=f"Unrecognized decision: {decision_raw}",
            )

        conn = self.db.connect()
        approval_repo = ApprovalRepository(conn)
        approval = approval_repo.get_approval(approval_id)

        if not approval:
            return CallbackResult(
                success=False,
                approval_id=approval_id,
                decision=decision_raw,
                actor_id=uid,
                message_text="",
                alert_text="طلب الاعتماد غير موجود في قاعدة البيانات.",
                error=f"Approval '{approval_id}' not found",
            )

        # Idempotency check: cannot resolve twice
        if approval.decision != ApprovalDecision.PENDING:
            return CallbackResult(
                success=False,
                approval_id=approval_id,
                decision=approval.decision.value,
                actor_id=approval.actor_id or "unknown",
                message_text=self._format_resolved_message(approval),
                alert_text=f"⚠️ تم اتخاذ القرار مسبقاً ({approval.decision.value}) بواسطة {approval.actor_id or 'المشغل'}.",
                error="Approval already resolved",
            )

        # Resolve in repository
        actor_label = f"admin_{uid}" if not user_name else f"{user_name} (ID: {uid})"
        success = approval_repo.resolve(
            approval_id=approval_id,
            decision=target_decision,
            actor_id=actor_label,
            notes=f"Resolved via Telegram interactive button callback by {actor_label}",
        )

        if not success:
            return CallbackResult(
                success=False,
                approval_id=approval_id,
                decision=decision_raw,
                actor_id=uid,
                message_text="",
                alert_text="حدث خطأ أثناء تحديث حالة الطلب.",
                error="Failed to persist approval resolution",
            )

        updated_approval = approval_repo.get_approval(approval_id)
        msg_text = self._format_resolved_message(updated_approval or approval)
        decision_labels = {
            ApprovalDecision.APPROVED: "✅ تم اعتماد الإجراء بنجاح!",
            ApprovalDecision.REJECTED: "❌ تم رفض الإجراء.",
            ApprovalDecision.REWRITE_REQUESTED: "✏️ تم تسجيل طلب التعديل.",
        }
        alert = decision_labels.get(target_decision, "تم تحديث الطلب.")

        return CallbackResult(
            success=True,
            approval_id=approval_id,
            decision=target_decision.value,
            actor_id=actor_label,
            message_text=msg_text,
            alert_text=alert,
        )

    def format_approval_card(self, approval: Approval) -> Dict[str, Any]:
        """Formats an interactive Telegram approval card with inline keyboard buttons."""
        text = (
            f"🔔 *طلب اعتماد إجراء جديد (Human Approval Required)*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• *رقم الطلب:* `{approval.approval_id}`\n"
            f"• *نوع الإجراء:* `{approval.action_type}`\n"
            f"• *الهدف:* `{approval.target_type}` (`{approval.target_id}`)\n"
            f"• *تاريخ الطلب:* `{approval.requested_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`\n"
        )
        if approval.notes:
            text += f"• *ملاحظات المشغل:* {approval.notes}\n"

        text += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *ملاحظة السياسة A-007:* لا يتم تنفيذ أو نشر أي إجراء خارجي دون موافقة صريحة."
        )

        keyboard = self.build_approval_keyboard(approval.approval_id)
        return {"text": text, "reply_markup": keyboard, "parse_mode": "Markdown"}

    @staticmethod
    def build_approval_keyboard(approval_id: str) -> Dict[str, Any]:
        """Builds standard Telegram Bot API inline keyboard markup."""
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ موافقة (Approve)",
                        "callback_data": f"appr:{approval_id}:approved",
                    },
                    {
                        "text": "❌ رفض (Reject)",
                        "callback_data": f"appr:{approval_id}:rejected",
                    },
                ],
                [
                    {
                        "text": "✏️ طلب تعديل (Rewrite)",
                        "callback_data": f"appr:{approval_id}:rewrite_requested",
                    }
                ],
            ]
        }

    # --- Internal Command Handlers ---

    def _cmd_help(self) -> CommandResponse:
        text = (
            "🤖 *لوحة تحكم مشغل Marketing OS (Telegram Control)*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "الأوامر المتاحة:\n"
            "• `/status` - عرض ملخص حالة النظام، الشركات، والعملاء.\n"
            "• `/leads [رمز الدولة]` - عرض أعلى العملاء المؤهلين (مثال: `/leads SA`).\n"
            "• `/pending` - استعراض كافة طلبات الاعتماد المعلقة مع أزرار الإجراء.\n"
            "• `/approve <ID>` - اعتماد طلب مباشرة عبر المعرّف.\n"
            "• `/reject <ID>` - رفض طلب مباشرة عبر المعرّف.\n"
            "• `/intake <القناة> <المرسل> <الرسالة>` - تسجيل محادثة واردة وتأهيل العميل آلياً.\n"
            "• `/help` - عرض هذه القائمة.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 *حدود الصلاحية:* الأوامر محصورة في المشرفين المعتمدين فقط (`A-026`)."
        )
        return CommandResponse(text=text)

    def _cmd_status(self) -> CommandResponse:
        conn = self.db.connect()
        company_repo = CompanyRepository(conn)
        lead_repo = LeadRepository(conn)
        approval_repo = ApprovalRepository(conn)

        all_leads = lead_repo.list_leads()
        qualified_leads = [l for l in all_leads if l.status == LeadStatus.QUALIFIED]
        discovered_leads = [l for l in all_leads if l.status == LeadStatus.DISCOVERED]
        rejected_leads = [l for l in all_leads if l.status == LeadStatus.REJECTED]
        pending_approvals = approval_repo.list_pending()

        text = (
            "📊 *ملخص حالة نظام Marketing OS*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"• *إجمالي العملاء المتتبعين:* {len(all_leads)}\n"
            f"  - 🌟 المؤهلين (Qualified): {len(qualified_leads)}\n"
            f"  - 🔍 قيد الاستكشاف (Discovered): {len(discovered_leads)}\n"
            f"  - ⛔ المستبعدين (Rejected): {len(rejected_leads)}\n"
            f"• *طلبات الاعتماد المعلقة:* {len(pending_approvals)}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 *حالة النظام:* متصل وقيد العمل بنمط SQLite WAL الآمن."
        )
        return CommandResponse(text=text)

    def _cmd_leads(self, country_code: Optional[str] = None) -> CommandResponse:
        conn = self.db.connect()
        lead_repo = LeadRepository(conn)
        company_repo = CompanyRepository(conn)

        qualified_leads = lead_repo.list_leads(status=LeadStatus.QUALIFIED)
        if country_code:
            target_cc = country_code.strip().upper()
            filtered = []
            for l in qualified_leads:
                comp = company_repo.get_company(l.company_id)
                if comp and comp.country_code.upper() == target_cc:
                    filtered.append(l)
            qualified_leads = filtered

        if not qualified_leads:
            msg = f"لا يوجد عملاء مؤهلين حالياً"
            if country_code:
                msg += f" في الدولة `{country_code.upper()}`"
            msg += ". يمكنك تشغيل مسح جديد لاكتشاف المزيد."
            return CommandResponse(text=msg)

        text = f"🌟 *أبرز العملاء المحتملين المؤهلين ({len(qualified_leads[:5])})*\n━━━━━━━━━━━━━━━━━━━━\n"
        for idx, lead in enumerate(qualified_leads[:5], 1):
            comp = company_repo.get_company(lead.company_id)
            comp_name = comp.canonical_name if comp else lead.company_id
            domain = comp.primary_domain if comp and comp.primary_domain else "غير متوفر"
            cc = comp.country_code if comp else "N/A"
            asm = lead_repo.get_latest_assessment(lead.lead_id)
            final_score = f"{asm.final_score:.2f}" if asm else "N/A"

            text += (
                f"*{idx}. {comp_name}* (أولوية: Bucket {lead.priority_bucket})\n"
                f"• الدولة: `{cc}` | النطاق: `{domain}`\n"
                f"• درجة التقييم: `{final_score}` | الخدمة: `{lead.recommended_service_key or 'عامة'}`\n"
                f"• معرّف العميل: `{lead.lead_id}`\n\n"
            )

        return CommandResponse(text=text.strip())

    def _cmd_pending(self) -> CommandResponse:
        conn = self.db.connect()
        approval_repo = ApprovalRepository(conn)
        pending = approval_repo.list_pending()

        if not pending:
            return CommandResponse(text="✅ *لا توجد طلبات اعتماد معلقة حالياً.* كل الإجراءات مكتملة.")

        first = pending[0]
        card = self.format_approval_card(first)
        if len(pending) > 1:
            card["text"] = f"📑 *(يوجد {len(pending)} طلبات معلقة)*\n\n" + card["text"]

        return CommandResponse(
            text=card["text"],
            reply_markup=card["reply_markup"],
        )

    def _cmd_direct_resolve(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        actor_id: str,
    ) -> CommandResponse:
        conn = self.db.connect()
        approval_repo = ApprovalRepository(conn)
        approval = approval_repo.get_approval(approval_id)

        if not approval:
            return CommandResponse(
                text=f"❌ طلب الاعتماد `{approval_id}` غير موجود.",
                success=False,
            )

        if approval.decision != ApprovalDecision.PENDING:
            return CommandResponse(
                text=f"⚠️ الطلب `{approval_id}` تم حسمه مسبقاً بحالة `{approval.decision.value}`.",
                success=False,
            )

        approval_repo.resolve(
            approval_id=approval_id,
            decision=decision,
            actor_id=actor_id,
            notes=f"Resolved via direct Telegram command by {actor_id}",
        )

        verb = "اعتماد" if decision == ApprovalDecision.APPROVED else "رفض"
        return CommandResponse(
            text=f"✅ تم {verb} الطلب `{approval_id}` بنجاح بواسطة المشرف `{actor_id}`.",
            success=True,
        )

    def _cmd_intake(self, args: List[str]) -> CommandResponse:
        """Processes inbound message, qualifies lead, drafts reply, and renders approval card."""
        if len(args) < 3:
            return CommandResponse(
                text=(
                    "ℹ️ *طريقة استخدام أمر إدخال المحادثات الواردة (/intake):*\n"
                    "`/intake <القناة> <معرف_المرسل> <نص_الرسالة>`\n\n"
                    "*أمثلة:*\n"
                    "• `/intake whatsapp +966501234567 نحتاج نظام أتمتة للمبيعات والفواتير`\n"
                    "• `/intake telegram @researcher أحتاج استشارة في التحليل الإحصائي للماجستير`\n"
                    "• `/intake email client@company.com نود مناقشة مشروع برمجة متجر إلكتروني`\n\n"
                    "🔒 *ملاحظة السياسات:* يتم فحص النزاهة الأكاديمية (A-008) وإخفاء الأسرار تلقائياً (I-05)."
                ),
                success=False,
            )

        channel = args[0]
        sender_ref = args[1]
        message_text = " ".join(args[2:])

        from marketing_plugin.services.conversation_intake import ConversationIntakeService
        service = ConversationIntakeService(db=self.db)
        outcome = service.ingest_message(
            channel=channel,
            external_party_ref=sender_ref,
            message_text=message_text,
            auto_request_approval=True,
        )

        if outcome.is_academic_violation:
            text = (
                "⛔ *تنبيه: تم رصد مخالفة لمعايير النزاهة الأكاديمية (A-008)*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"• *القناة:* `{channel.upper()}`\n"
                f"• *المرسل:* `{sender_ref}`\n"
                f"• *الإجراء المتخذ:* تم استبعاد العميل تلقائياً (`REJECTED`) وتسجيل المخالفة.\n"
                f"• *معرّف التفاعل:* `{outcome.interaction_id}`\n\n"
                f"📋 *مسودة الرد الأخلاقي المقترح:*\n"
                f"_{outcome.suggested_reply}_\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ *ملاحظة:* تم إيقاف أي إجراءات تسويقية لهذا الطلب بموجب السياسة A-008."
            )
            return CommandResponse(text=text, success=True)

        approval_conn = self.db.connect()
        company_repo = CompanyRepository(approval_conn)
        company = company_repo.get_company(outcome.company_id) if outcome.company_id else None
        comp_name = company.canonical_name if company else "عميل محتمل"

        text = (
            "📥 *تم استقبال محادثة واردة وتأهيل العميل بنجاح*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"• *الجهة / العميل:* *{comp_name}*\n"
            f"• *القناة:* `{channel.upper()}` | *المرسل:* `{sender_ref}`\n"
            f"• *مسار العمل (Funnel):* `{outcome.funnel.upper()}` | *النية:* `{outcome.intent}`\n"
            f"• *معرّف العميل:* `{outcome.lead_id}`\n"
            f"• *معرّف التفاعل:* `{outcome.interaction_id}`\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💬 *مسودة الرد المقترحة (مسودة AI - بانتظار الاعتماد):*\n"
            f"_{outcome.suggested_reply}_\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ *السياسة A-007 / A-022:* يتطلب الرد موافقة المشغل البشري قبل إرساله."
        )

        reply_markup = None
        if outcome.approval_id:
            reply_markup = self.build_approval_keyboard(outcome.approval_id)

        return CommandResponse(
            text=text,
            reply_markup=reply_markup,
            success=True,
        )

    @staticmethod
    def _format_resolved_message(approval: Approval) -> str:
        icon = "✅" if approval.decision == ApprovalDecision.APPROVED else ("❌" if approval.decision == ApprovalDecision.REJECTED else "✏️")
        resolved_time = approval.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC') if approval.resolved_at else "الآن"
        return (
            f"{icon} *تم حسم طلب الاعتماد بنجاح*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• *رقم الطلب:* `{approval.approval_id}`\n"
            f"• *نوع الإجراء:* `{approval.action_type}`\n"
            f"• *القرار النهائي:* `{approval.decision.value.upper()}`\n"
            f"• *بواسطة المشرف:* `{approval.actor_id or 'مجهول'}`\n"
            f"• *تاريخ الحسم:* `{resolved_time}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 *التدقيق الأمني:* تم حفظ السجل وتثبيته في قاعدة البيانات (`A-026`)."
        )
