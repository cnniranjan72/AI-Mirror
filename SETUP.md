# AIMirror — Local Setup Guide

Get the backend, dashboard, and browser extension running locally after cloning from GitHub. This
guide reflects the current V3 architecture (Identity/Evidence/Inference pipeline, dashboard, auth,
and dual Instagram+YouTube ingestion) — not the earlier V1/V2 persona-archetype system some older
docs in this repo still describe.

## Prerequisites

- **Python 3.11+** (built and tested on 3.13)
- **Node.js 18+** (tested on 22) and npm
- **A PostgreSQL database with the `pgvector` extension** — [Neon](https://neon.tech) has a free tier and is what this project was built against; any Postgres with pgvector works. There is no SQLite or offline fallback — `DATABASE_URL` is required and the backend refuses to start without it.
- **Either** [Ollama](https://ollama.com) (free, runs locally, no API costs) **or** an OpenAI/Anthropic API key, for the LLM verbalization layer

## 1. Clone

```bash
git clone <this-repo-url>
cd AI-Mirror
```

## 2. Backend

```bash
cd backend
python -m venv venv
```

Activate it:
- Windows (Git Bash): `source venv/Scripts/activate`
- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- Mac/Linux: `source venv/bin/activate`

```bash
pip install -r requirements.txt
```

### Configure

Create **`backend/.env`**:

```env
# Required — no fallback. Get a free Postgres+pgvector database at
# https://console.neon.tech
DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require

# LLM verbalization layer — the ONLY place an LLM is used. By design it
# never reasons or decides anything; it only turns already-decided facts
# (produced by the deterministic pipeline) into prose.
LLM_PROVIDER=ollama          # "ollama" (local/free), "openai", or "anthropic"
OLLAMA_BASE_URL=http://localhost:11434/v1
LLM_MODEL_OLLAMA=llama3.2
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=

# Signs auth tokens. Defaults to a placeholder — set your own random
# value before this backend is reachable by anyone besides you (see
# "Known limitations" below for why this matters).
AUTH_SECRET=change-me-to-something-random

PORT=8000
LOG_LEVEL=INFO
```

**If using Ollama:** install it, then pull the model once:
```bash
ollama pull llama3.2
```
Ollama runs as a local background service on port 11434 automatically after install.

### Run

From **inside `backend/`**, with the venv active — this exact form (run from the `backend/`
directory, both repo root and `backend/` on `PYTHONPATH`) is what's actually been verified working
throughout this project's development:

```bash
# Git Bash / macOS / Linux (adjust the path to your clone location):
PYTHONPATH="/path/to/AI-Mirror:/path/to/AI-Mirror/backend" python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
```powershell
# PowerShell:
$env:PYTHONPATH = "C:\path\to\AI-Mirror;C:\path\to\AI-Mirror\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

You do **not** need to run any separate database-setup script — every migration applies
automatically on startup. The log should end with something like `Migration V10 applied
successfully` and `Database ready`. Verify with:

```bash
curl http://127.0.0.1:8000/health
```
You should get back `{"status":"healthy", ...}`.

**If you see `ModuleNotFoundError: No module named 'backend'` or `'app'`** — `PYTHONPATH` isn't set
correctly, or you're not running from inside `backend/`. See Troubleshooting below.

## 3. Dashboard

```bash
cd dashboard
npm install
```

Create **`dashboard/.env`**:

```env
VITE_API_URL=http://localhost:8000
VITE_USER_ID=demo_user
```

(`VITE_USER_ID` is only the fallback used before you sign in — see the next step.)

```bash
npm run dev
```

Open **http://localhost:5173**.

## 4. Create your own account

Each person testing this should sign up for their **own** account rather than sharing one
username — that's what keeps a twin's data associated with just that person (see "Known
limitations" for exactly what that isolation does and doesn't guarantee).

1. Click **Sign in** at the bottom of the sidebar → switch to Register
2. Pick a username and a password (6+ characters)
3. You're logged in — every page now reflects your own (empty, at first) cognitive twin

## 5. Browser extension (live tracking)

1. Open `chrome://extensions`, enable **Developer mode** (top right)
2. **Load unpacked** → select the `chrome-extension/` folder from this repo
3. Browse `instagram.com/reels` or `youtube.com` (both watch pages and Shorts are tracked) — the extension batches events and sends them to the backend automatically
4. Check the **Import** tab in the dashboard to see your live source mix once you've watched a few things

A dashboard code change never requires reloading the extension; the reverse is not true — reload
the extension at `chrome://extensions` after any change to files inside `chrome-extension/`.

## 6. Fastest way to see data (no browsing required)

Open the **Import** tab and click **Run demo seed** — it sends synthetic events through the real
pipeline (same code path as live tracking) so behavior objects, evidence, inferences, and an
identity appear immediately.

## Known limitations (read before giving others access)

- **User isolation is enforced by data scoping, not by request authorization.** Every table is
  correctly scoped by `user_id` (verified: a fresh account returns zero rows — no bleed from any
  other user), and the dashboard always sends the logged-in user's own id — but the backend's read
  endpoints do not check that a request's `user_id` actually matches the caller's auth token.
  Fine for testing on a trusted local machine or private network; **do not expose this backend on
  the open internet as-is**, since anyone who can reach it can read any known username's data.
- `AUTH_SECRET` defaults to a placeholder if unset — change it before this leaves your machine, since it's what makes login tokens un-forgeable.
- No automated test suite yet. Changes are verified by actually running the app (curling the API, clicking through the dashboard).
- The Instagram/YouTube extractors read the live page DOM (plus, for YouTube, an embedded page-data JSON) — both platforms can change their markup at any time, which would require updating the corresponding content script.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ValueError: DATABASE_URL environment variable is required` | `backend/.env` is missing, or uvicorn isn't being run from inside `backend/` |
| `ModuleNotFoundError: No module named 'backend'` / `'app'` | `PYTHONPATH` isn't set to include both the repo root and `backend/` |
| First chat/ingest request hangs ~1-2 minutes | Ollama cold-loading the model on its first call — normal; later requests are fast |
| `Address already in use` on port 8000 or 5173 | Something else is already listening — stop it, or change `PORT` / pass Vite a different port |
| Dashboard loads but every page is empty | Not signed in yet (still on the `VITE_USER_ID` fallback with no data) — register/sign in, or click "Run demo seed" on Import |
| Extension console shows no `[AIMirror]` logs on Instagram/YouTube | Reload the extension at `chrome://extensions`, then hard-refresh the page |

## Where to go next

- **Guide** tab in the dashboard (`/guide`) — what each page does and how to use it
- **Documentation** tab (`/documentation`) — the full cognitive pipeline, key-concept glossary, and data-source details
