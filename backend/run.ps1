Set-Location $PSScriptRoot
$ErrorActionPreference = "Stop"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv is not on PATH. Install from https://docs.astral.sh/uv/"
}
uv sync --python 3.12
Write-Host "Starting API + UI at http://127.0.0.1:8000/ (set OPENAI_API_KEY in backend/.env)" -ForegroundColor Green
uv run uvicorn app.main:app --reload --reload-exclude ".venv" --reload-exclude "__pycache__" --host 127.0.0.1 --port 8000
