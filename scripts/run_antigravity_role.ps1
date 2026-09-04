param(
  [Parameter(Mandatory=$true)][ValidateSet("orchestrator","explorer","builder","verifier","reviewer","heavy-reviewer")][string]$Agent,
  [Parameter(Mandatory=$true)][string]$Prompt,
  [ValidateSet("text","json","stream-json")][string]$OutputFormat = "json"
)
agy -p $Prompt --agent $Agent --model gemini-3.8-flash-high --effort high --output-format $OutputFormat
exit $LASTEXITCODE
