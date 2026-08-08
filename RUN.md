# AIMirror — Run Commands

Quick reference for running every service. Copy-paste these commands.

> Just want to look at it without running anything locally? It's deployed:
> **https://aimirror-dashboard.onrender.com** (backend: https://aimirror-backend-cu00.onrender.com). Free tier — first request after ~15 min idle takes 30-60s to wake up.

## Supervised (auto-restart + crash logs)

The manual commands below work fine, but nothing watches the process — if it
crashes (or dies for an unclear reason, which has happened), it just stays
down with no record of why. `scripts\start-all.ps1` runs the backend and
dashboard under a small supervisor that restarts on exit and keeps a real
stdout/stderr log per attempt plus a `logs\supervisor.log` of every
start/exit/restart. Does not (yet) cover `behavioral-engine/`.

```powershell
cd C:\Users\cnnir\Documents\AI-Mirror
.\scripts\start-all.ps1     # starts backend (8000) + dashboard (5173), supervised
.\scripts\stop-all.ps1      # stops both, including their process trees
Get-Content .\logs\supervisor.log -Tail 20 -Wait   # watch restarts live
```

Logs land in `logs\` (gitignored): `logs\<service>_stdout_<attempt>.log`,
`logs\<service>_stderr_<attempt>.log` (a fresh file per restart, so an old
crash trace is never overwritten by the next attempt), and `logs\supervisor.log`.

## Ports Summary

| Service | Port | Notes |
|---|---|---|
| Main Backend (`backend/`) | **8000** | Dashboard's `VITE_API_URL` points here |
| Behavioral Engine (`behavioral-engine/`) | **3000** | Separate service |
| Dashboard (`dashboard/`) | **5173** | Vite dev server |

---

## 0. Virtual Environments

Each Python service has its own venv (do **not** share them).

- Main backend: `backend\venv\Scripts\python.exe`
- Behavioral engine: `behavioral-engine\venv\Scripts\python.exe`

---

## 1. Main Backend — port 8000

Run from **inside** `backend/`. `PYTHONPATH` must include both the repo root and `backend/`.

```powershell
# PowerShell (verified)
cd C:\Users\cnnir\Documents\AI-Mirror\backend
$env:PYTHONPATH = "C:\Users\cnnir\Documents\AI-Mirror;C:\Users\cnnir\Documents\AI-Mirror\backend"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# Git Bash / macOS / Linux
cd /path/to/AI-Mirror/backend
PYTHONPATH="/path/to/AI-Mirror:/path/to/AI-Mirror/backend" ./venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify: `curl http://127.0.0.1:8000/health` → `{"status":"healthy",...}`

### Fix a broken/corrupted backend venv

The backend venv can break if packages were installed for the wrong Python version
(`cp313` wheels on a `cp311` venv). Reinstall the C-extension packages:

```powershell
cd C:\Users\cnnir\Documents\AI-Mirror\backend
.\venv\Scripts\python.exe -m pip install --force-reinstall --no-cache-dir psycopg2-binary asyncpg scikit-learn
```

---

## 2. Behavioral Engine — port 3000

Run from **inside** `behavioral-engine/`.

```powershell
# PowerShell
cd C:\Users\cnnir\Documents\AI-Mirror\behavioral-engine
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

```bash
# Git Bash / macOS / Linux
cd /path/to/AI-Mirror/behavioral-engine
./venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Verify: `curl http://localhost:3000/health` → `{"status":"healthy","vector_store":"connected",...}`

---

## 3. Dashboard — port 5173

```powershell
cd C:\Users\cnnir\Documents\AI-Mirror\dashboard
npm install
npm run dev
```

Open **http://localhost:5173**.

Dashboard env (`dashboard\.env`):
```
VITE_API_URL=http://localhost:8000
VITE_USER_ID=test_user_001
```

---

## 4. Browser Extension (live tracking)

1. Open `chrome://extensions`, enable **Developer mode**
2. **Load unpacked** → select the `chrome-extension/` folder
3. It defaults to the **deployed backend** (`https://aimirror-backend-cu00.onrender.com`). For local dev against the servers above instead, open the popup → **⚙️ Connection settings** and set Backend URL to `http://localhost:8000` and Dashboard URL to `http://localhost:5173`.
4. Browse `instagram.com/reels` or `youtube.com`
5. Reload the extension after any change to `chrome-extension/`

---

## 5. Fastest way to see data (no browsing)

Open the dashboard **Import** tab → **Run demo seed** (sends synthetic events through the real pipeline).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'backend'` / `'app'` | `PYTHONPATH` isn't set — must include repo root **and** `backend/`, and run from inside `backend/` |
| `Address already in use` on port 8000 | Something else is on 8000 (e.g. old backend). Stop it: `Get-NetTCPConnection -LocalPort 8000 \| Stop-Process -Id {$_.OwningProcess} -Force` |
| Dashboard loads but pages are empty | Not signed in — register/sign in, or click **Run demo seed** on Import |
| First chat/ingest request hangs ~1-2 min | Ollama cold-loading the model on first call — normal |
