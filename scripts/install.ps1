# Local alias — Grok-style installer is build.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $here "build.ps1") @args