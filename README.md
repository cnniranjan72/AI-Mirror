# AIMirror – Behavioral Digital Twin for Social Media Transparency

## Phase 1 MVP

A consent-based, client-side behavioral tracking system for Instagram Reels that captures user interaction patterns, stores data locally, and provides analytics through a dashboard.

## 🎯 What This Does

1. **Chrome Extension** - Observes your Instagram Reels behavior (watch time, likes, scrolls)
2. **Backend API** - Stores behavioral data and provides analytics
3. **Dashboard** - Visualizes your usage patterns and statistics

## 🏗 Architecture

```
├── chrome-extension/     # Manifest V3 Chrome Extension
│   ├── manifest.json
│   ├── content.js       # Instagram DOM observer
│   ├── background.js    # Service worker for data batching
│   └── popup/           # Extension popup UI
├── backend/             # FastAPI + Neon PostgreSQL
│   ├── main.py          # FastAPI application
│   ├── database.py      # Neon PostgreSQL connection
│   ├── models.py        # Pydantic models
│   └── requirements.txt
└── dashboard/           # React + Vite web app
    └── src/
```

## 🚀 Quick Start

### 1. Backend Setup

**First, get your Neon database URL:**
1. Go to https://console.neon.tech/ (free tier available)
2. Create a new project
3. Copy your connection string

**Then setup the backend:**

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your DATABASE_URL
python main.py
```

Backend runs on `http://localhost:3000`

**API Documentation:** http://localhost:3000/docs

### 2. Chrome Extension Setup

1. Open Chrome → `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `chrome-extension` folder

### 3. Dashboard Setup

```bash
cd dashboard
npm install
npm run dev
```

Dashboard runs on `http://localhost:5173`

## 📊 Features

### Chrome Extension
- ✅ Detects Instagram Reels automatically
- ✅ Tracks watch time per reel
- ✅ Captures likes, scrolls, and replay behavior
- ✅ Batches data every 60 seconds
- ✅ Stores locally in chrome.storage

### Backend API
- ✅ POST /api/events - Receive behavioral events
- ✅ GET /api/sessions - List all sessions
- ✅ GET /api/analytics - Aggregate statistics

### Dashboard
- ✅ Overview stats (total watch time, sessions)
- ✅ Session timeline view
- ✅ Behavioral FastAPI (Python) (Neon Postge SQLtio, Alchrmyoll speed)
, React Router
## ⚠️ Privacy & Ethics

- **No scraping** - Only observes DOM elements
- **Consent-based** - User must install extension
- **Local-first** - Data stored locally before sync
- **Transparent** - All code is open and auditable

## 🔧 Technical Stack

- **Extension**: Vanilla JS, Manifest V3
- **Backend**: Node.js, Express, SQLite
- **Dashboard**: React, Vite, Recharts

## 📝 Data Format

Each behavioral event:

```json
{
  "reel_id": "C8xYz...",
  "username": "example_user",
  "caption": "Check this out...",
  "liked": true,
  "watch_time": 5.2,
  "replay_count": 0,
  "scroll_speed": 1.1,
  "timestamp": "2026-04-08T06:51:00.000Z"
}
```

## 🎯 Phase 1 Limitations

- No ML models yet
- No recommendation analysis
- Basic analytics only
- Single-user system

## 📈 Future Phases

- Phase 2: Behavioral modeling & pattern detection
- Phase 3: RL-based digital twin
- Phase 4: Transparency tools & insights

## 📄 License

MIT License - See LICENSE file for details
