# Legacy Security Note

The inspected Clients Hunter archive included a `.env` and a Firebase service-account JSON in the archive contents, even though Git ignored them. Do not copy those files or their values into Marketing OS. If any legacy credentials are still active, rotate/revoke them outside this repository.

Only sanitized code snippets, public source behavior notes, and de-identified/non-secret regression fixtures may cross the quarantine boundary.
