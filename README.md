# Trackline

Trackline is currently at Milestone 0. This repository contains only the local development foundation: a Next.js frontend, a FastAPI backend, one placeholder worker process, and PostgreSQL development configuration. Song/version product functionality is intentionally not implemented yet.

## Prerequisites

- Node.js 20.9 or newer
- Python 3.12 or newer
- Docker with Docker Compose, when running the complete stack

On Windows PowerShell, use `npm.cmd` in place of `npm` if the local execution policy blocks the `npm.ps1` shim.

## Initial setup

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Install the frontend dependencies:

```powershell
Set-Location frontend
npm ci
Set-Location ..
```

Create the backend virtual environment and install its development dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".\backend[dev]"
```

On macOS or Linux, replace the final command with:

```bash
./.venv/bin/python -m pip install -e "./backend[dev]"
```

## Run locally

Start the backend from the repository root:

```powershell
.\.venv\Scripts\python -m uvicorn api.main:app --app-dir backend --reload
```

Start the frontend in a second terminal:

```powershell
Set-Location frontend
npm run dev
```

The frontend is available at <http://localhost:3000>. The backend health endpoint is available at <http://localhost:8000/health>.

To run the complete development stack, including PostgreSQL and the placeholder worker:

```powershell
docker compose up --build
```

## Verification commands

Frontend:

```powershell
Set-Location frontend
npm run format
npm run lint
npm run typecheck
npm test
npm run build
```

Backend, from the repository root:

```powershell
.\.venv\Scripts\ruff format --check backend
.\.venv\Scripts\ruff check backend
.\.venv\Scripts\mypy backend
.\.venv\Scripts\pytest backend
```

The worker is an environment placeholder only. It does not claim or process research jobs yet.
