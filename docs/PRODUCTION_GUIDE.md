# AIMirror - Production Deployment Guide

## 🎯 System Overview

**AIMirror** is a complete adaptive behavioral AI system that:
- Captures Instagram Reels usage via Chrome Extension
- Processes behavioral data with AI (FastAPI + ChromaDB + RL)
- Provides insights, chat, and adaptive suggestions
- Displays analytics in a beautiful React dashboard

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  CHROME EXTENSION                        │
│  - Captures Instagram events                            │
│  - Sends to background.js                               │
│  - Batches and POSTs to backend                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              BACKEND (FastAPI + Python)                  │
│  - Event ingestion & feature engineering                │
│  - Embeddings (sentence-transformers)                   │
│  - Vector storage (ChromaDB)                            │
│  - RL system (contextual bandit)                        │
│  - RAG chat with AI Mirror                              │
│  - Impact analysis & persona generation                 │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           DASHBOARD (React + TailwindCSS)                │
│  - Real-time analytics                                  │
│  - AI Mirror chat interface                             │
│  - Persona visualization                                │
│  - Action suggestions with feedback                     │
│  - Trend analysis & insights                            │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Part 1: Backend Setup

### Prerequisites

- Python 3.9+
- pip
- Virtual environment (recommended)

### Installation Steps

```bash
# 1. Navigate to backend directory
cd behavioral-engine

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. First run will download sentence-transformers model (~80MB)
# This happens automatically on startup
```

### Start Backend Server

```bash
uvicorn app.main:app --reload --port 8000
```

**Server will be available at:** `http://localhost:8000`

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "vector_store": "connected",
#   "collection_count": 0
# }
```

### Database Setup

**ChromaDB Storage:**
- Location: `./chroma_db/`
- Auto-created on first run
- Persistent across restarts

**Reset Database:**
```bash
# Stop server, then:
rm -rf chroma_db/
rm -rf alignment_data/
rm -rf rl_data/
rm -rf chat_data/

# Restart server - fresh database
```

**Inspect Database:**
```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("behavioral_memory")
print(f"Items: {collection.count()}")
```

---

## 📦 Part 2: Chrome Extension Setup

### Installation

```bash
# 1. Navigate to extension directory
cd chrome-extension

# 2. Open Chrome and go to:
chrome://extensions/

# 3. Enable "Developer mode" (top right)

# 4. Click "Load unpacked"

# 5. Select the chrome-extension folder

# 6. Extension will appear in toolbar
```

### Backend Integration

The extension needs to send data to the backend. Update `background.js`:

```javascript
// background.js - Add at the top
const BACKEND_URL = 'http://localhost:8000';
let userId = null;
let eventBuffer = [];

// Initialize user ID
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(['userId'], (result) => {
    if (!result.userId) {
      userId = 'user_' + Math.random().toString(36).substr(2, 9);
      chrome.storage.local.set({ userId });
      console.log('[AIMirror] Generated user ID:', userId);
    } else {
      userId = result.userId;
      console.log('[AIMirror] Loaded user ID:', userId);
    }
  });
});

// Listen for events from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'REEL_EVENT') {
    eventBuffer.push(message.event);
    console.log('[AIMirror] Buffered event:', eventBuffer.length);
    
    // Send batch every 30 seconds or 10 events
    if (eventBuffer.length >= 10) {
      sendBatchToBackend();
    }
  }
});

// Send batch to backend
async function sendBatchToBackend() {
  if (eventBuffer.length === 0) return;
  
  const batch = [...eventBuffer];
  eventBuffer = [];
  
  try {
    const response = await fetch(`${BACKEND_URL}/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events: batch })
    });
    
    if (response.ok) {
      console.log('[AIMirror] Sent batch:', batch.length, 'events');
    } else {
      console.error('[AIMirror] Backend error:', response.status);
      // Re-add events to buffer for retry
      eventBuffer.unshift(...batch);
    }
  } catch (error) {
    console.error('[AIMirror] Network error:', error);
    // Re-add events to buffer for retry
    eventBuffer.unshift(...batch);
  }
}

// Periodic batch send (every 30 seconds)
setInterval(sendBatchToBackend, 30000);

// Send on browser close
chrome.runtime.onSuspend.addListener(() => {
  sendBatchToBackend();
});
```

### Update Content Script

In `content.js`, send events to background:

```javascript
// In recordEvent function, add:
function recordEvent(eventType, data) {
  const event = {
    reel_id: data.reel_id || generateReelId(),
    username: data.username || 'unknown',
    watch_time: data.watch_time || 0,
    liked: data.liked || false,
    timestamp: new Date().toISOString(),
    session_id: state.sessionId
  };
  
  // Send to background
  chrome.runtime.sendMessage({
    type: 'REEL_EVENT',
    event: event
  });
  
  console.log('[AIMirror] Recorded event:', eventType, event);
}
```

### Testing Extension

1. Open Instagram Reels: `https://www.instagram.com/reels/`
2. Scroll through a few reels
3. Check console logs (F12): Should see `[AIMirror]` messages
4. Check backend logs: Should see ingestion messages
5. Query backend: `curl http://localhost:8000/health`

---

## 📦 Part 3: React Dashboard Setup

### Create Dashboard

```bash
# 1. Create React app with Vite
npm create vite@latest aimirror-dashboard -- --template react

# 2. Navigate to project
cd aimirror-dashboard

# 3. Install dependencies
npm install

# 4. Install additional packages
npm install tailwindcss postcss autoprefixer
npm install framer-motion
npm install axios
npm install recharts
npm install lucide-react

# 5. Initialize Tailwind
npx tailwindcss init -p
```

### Configure Tailwind

**tailwind.config.js:**
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#6366f1',
        secondary: '#8b5cf6',
      },
    },
  },
  plugins: [],
}
```

**src/index.css:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-gray-900 text-white;
}
```

### API Service Layer

**src/services/api.js:**
```javascript
import axios from 'axios';

const API_BASE = 'http://localhost:8000';
const USER_ID = 'user_123'; // Get from localStorage or auth

export const api = {
  // Profile
  async fetchProfile() {
    const response = await axios.get(`${API_BASE}/profile`);
    return response.data;
  },
  
  // Chat
  async sendChatMessage(query) {
    const response = await axios.post(`${API_BASE}/chat`, {
      user_id: USER_ID,
      query: query,
      include_context: true
    });
    return response.data;
  },
  
  async getChatHistory() {
    const response = await axios.get(`${API_BASE}/chat/history/${USER_ID}`);
    return response.data;
  },
  
  // Actions
  async getAction() {
    const response = await axios.post(`${API_BASE}/action`, {
      user_id: USER_ID
    });
    return response.data;
  },
  
  async sendFeedback(actionId, followed, rating) {
    const response = await axios.post(`${API_BASE}/feedback`, {
      user_id: USER_ID,
      action_id: actionId,
      followed: followed,
      user_rating: rating
    });
    return response.data;
  },
  
  // Insights
  async queryInsights(query) {
    const response = await axios.post(`${API_BASE}/query`, {
      query: query,
      top_k: 5
    });
    return response.data;
  },
  
  // Alignment
  async setGoal(goal, targetWatchTime) {
    const response = await axios.post(`${API_BASE}/alignment`, {
      user_id: USER_ID,
      goal: goal,
      target_watch_time: targetWatchTime,
      priority: 'high'
    });
    return response.data;
  }
};
```

### Dashboard Components

**src/App.jsx:**
```javascript
import { useState } from 'react';
import { motion } from 'framer-motion';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Persona from './pages/Persona';
import Actions from './pages/Actions';
import Insights from './pages/Insights';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  
  const pages = {
    dashboard: <Dashboard />,
    chat: <Chat />,
    persona: <Persona />,
    actions: <Actions />,
    insights: <Insights />
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900">
      {/* Navigation */}
      <nav className="bg-black/30 backdrop-blur-lg border-b border-white/10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              AIMirror
            </h1>
            <div className="flex gap-4">
              {['dashboard', 'chat', 'persona', 'actions', 'insights'].map((page) => (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className={`px-4 py-2 rounded-lg transition-all ${
                    currentPage === page
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-300 hover:bg-white/10'
                  }`}
                >
                  {page.charAt(0).toUpperCase() + page.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </nav>
      
      {/* Page Content */}
      <motion.div
        key={currentPage}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="container mx-auto px-6 py-8"
      >
        {pages[currentPage]}
      </motion.div>
    </div>
  );
}

export default App;
```

**src/pages/Dashboard.jsx:**
```javascript
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { api } from '../services/api';
import { Activity, Clock, Target, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadProfile();
  }, []);
  
  async function loadProfile() {
    try {
      const data = await api.fetchProfile();
      setProfile(data);
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setLoading(false);
    }
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-purple-500"></div>
      </div>
    );
  }
  
  if (!profile || profile.status === 'no_data') {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400 text-lg">No data yet. Start using Instagram to build your profile.</p>
      </div>
    );
  }
  
  const metrics = profile.persona?.metrics || {};
  
  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold">Dashboard</h2>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={<Clock />}
          label="Total Watch Time"
          value={`${(metrics.total_reels * 3 / 60).toFixed(0)} min`}
          color="purple"
        />
        <StatCard
          icon={<Activity />}
          label="Sessions"
          value={metrics.total_sessions || 0}
          color="blue"
        />
        <StatCard
          icon={<Target />}
          label="Attention Score"
          value={(metrics.attention_score * 100).toFixed(0) + '%'}
          color="green"
        />
        <StatCard
          icon={<TrendingUp />}
          label="Engagement"
          value={(metrics.engagement_score * 100).toFixed(0) + '%'}
          color="pink"
        />
      </div>
      
      {/* Persona Card */}
      {profile.persona && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10"
        >
          <h3 className="text-xl font-bold mb-4">Your Behavioral Archetype</h3>
          <div className="space-y-3">
            <p className="text-2xl font-bold text-purple-400">{profile.persona.archetype}</p>
            <p className="text-gray-300">{profile.persona.summary}</p>
          </div>
        </motion.div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  const colors = {
    purple: 'from-purple-500 to-purple-700',
    blue: 'from-blue-500 to-blue-700',
    green: 'from-green-500 to-green-700',
    pink: 'from-pink-500 to-pink-700'
  };
  
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10"
    >
      <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${colors[color]} flex items-center justify-center mb-4`}>
        {icon}
      </div>
      <p className="text-gray-400 text-sm">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
    </motion.div>
  );
}
```

### Start Dashboard

```bash
npm run dev
```

**Dashboard will be available at:** `http://localhost:5173`

---

## 🔄 Part 4: End-to-End Testing

### Complete Test Flow

```bash
# 1. Start Backend
cd behavioral-engine
uvicorn app.main:app --reload --port 8000

# 2. Start Dashboard (new terminal)
cd aimirror-dashboard
npm run dev

# 3. Load Extension
# - Open chrome://extensions/
# - Load unpacked: chrome-extension folder

# 4. Test Data Flow
# - Open Instagram Reels
# - Scroll through 5-10 reels
# - Wait 30 seconds for batch send
# - Check backend logs for ingestion

# 5. Test Dashboard
# - Open http://localhost:5173
# - Should see profile data
# - Try chat interface
# - Get action suggestion
# - Submit feedback
```

### Manual API Testing

```bash
# 1. Ingest sample data
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "reel_id": "test1",
        "username": "creator1",
        "watch_time": 5.2,
        "liked": true,
        "timestamp": "2026-04-08T10:00:00Z",
        "session_id": "session_1"
      },
      {
        "reel_id": "test2",
        "username": "creator2",
        "watch_time": 2.1,
        "liked": false,
        "timestamp": "2026-04-08T10:01:00Z",
        "session_id": "session_1"
      }
    ]
  }'

# 2. Set goal
curl -X POST http://localhost:8000/alignment \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "goal": "reduce reels usage",
    "target_watch_time": 30,
    "priority": "high"
  }'

# 3. Get action
curl -X POST http://localhost:8000/action \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123"}'

# 4. Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "query": "Why am I scrolling so much?",
    "include_context": true
  }'

# 5. Get profile
curl http://localhost:8000/profile
```

---

## 📁 Project Structure

```
AI-Mirror/
├── behavioral-engine/           # Backend (FastAPI)
│   ├── app/
│   │   ├── main.py             # FastAPI app
│   │   ├── api/                # API endpoints
│   │   ├── services/           # Business logic
│   │   └── models/             # Pydantic schemas
│   ├── chroma_db/              # Vector database
│   ├── alignment_data/         # User goals
│   ├── rl_data/                # RL parameters
│   ├── chat_data/              # Chat history
│   └── requirements.txt
│
├── chrome-extension/           # Chrome Extension
│   ├── manifest.json
│   ├── content.js              # Instagram tracker
│   └── background.js           # Backend integration
│
└── aimirror-dashboard/         # React Dashboard
    ├── src/
    │   ├── pages/              # Dashboard pages
    │   ├── services/           # API layer
    │   └── App.jsx
    └── package.json
```

---

## 🎯 Success Criteria

✅ **Extension captures Instagram events**
✅ **Backend processes and stores data**
✅ **Dashboard displays analytics**
✅ **Chat provides insights**
✅ **RL suggests actions**
✅ **Feedback loop updates system**

---

## 🚀 Production Deployment

### Backend (Cloud)

```bash
# Deploy to Heroku, Railway, or Render
# Add Procfile:
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT

# Environment variables:
DATABASE_URL=<postgres_url>  # Optional: migrate from ChromaDB
```

### Dashboard (Vercel/Netlify)

```bash
# Build for production
npm run build

# Deploy to Vercel
vercel deploy

# Update API_BASE in api.js to production URL
```

### Extension (Chrome Web Store)

1. Zip extension folder
2. Submit to Chrome Web Store
3. Update manifest with production backend URL

---

## 🔧 Troubleshooting

**Extension not sending data:**
- Check console logs (F12)
- Verify backend URL in background.js
- Check CORS settings in backend

**Backend errors:**
- Check Python version (3.9+)
- Verify all dependencies installed
- Check ChromaDB permissions

**Dashboard not loading:**
- Verify backend is running
- Check API_BASE URL in api.js
- Check browser console for errors

---

## 📚 Documentation

- **README.md** - System overview
- **QUICKSTART.md** - Quick start guide
- **ADAPTIVE_SYSTEM.md** - RL & RAG documentation
- **PRODUCTION_GUIDE.md** - This file

---

**Built with ❤️ for AIMirror - Your Adaptive Behavioral Digital Twin**
