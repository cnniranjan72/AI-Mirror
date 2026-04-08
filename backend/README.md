# AIMirror Backend API

FastAPI backend with Neon PostgreSQL for storing and analyzing Instagram Reels behavioral data.

## 🚀 Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Then edit `.env` and add your Neon database URL:

```env
DATABASE_URL=postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

**Get your Neon database URL:**
1. Go to https://console.neon.tech/
2. Create a new project (free tier available)
3. Copy the connection string
4. Paste it into your `.env` file

### 3. Run the Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

The API will be available at `http://localhost:3000`

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:3000/docs
- **ReDoc**: http://localhost:3000/redoc

## 🔌 API Endpoints

### POST /api/events
Store behavioral events from a session.

**Request Body:**
```json
{
  "session_id": "session_123",
  "start_time": "2026-04-08T06:51:00.000Z",
  "end_time": "2026-04-08T07:00:00.000Z",
  "events": [
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
  ]
}
```

### GET /api/sessions
List all sessions with pagination.

**Query Parameters:**
- `limit` (default: 50)
- `offset` (default: 0)

### GET /api/sessions/{session_id}
Get details of a specific session.

### GET /api/sessions/{session_id}/events
Get all events for a specific session.

### GET /api/events
List all events with pagination.

**Query Parameters:**
- `limit` (default: 100)
- `offset` (default: 0)

### GET /api/analytics
Get aggregate analytics across all sessions.

**Response:**
```json
{
  "total_sessions": 10,
  "total_events": 150,
  "total_watch_time": 780.5,
  "avg_watch_time_per_reel": 5.2,
  "avg_watch_time_per_session": 78.05,
  "like_ratio": 35.5,
  "avg_scroll_speed": 1.2,
  "reels_per_session": 15.0,
  "most_watched_users": [...],
  "total_replays": 12
}
```

### DELETE /api/sessions/{session_id}
Delete a session and all its events.

### GET /health
Health check endpoint.

## 🗄️ Database Schema

### Sessions Table
- `id` - Primary key
- `session_id` - Unique session identifier
- `start_time` - Session start timestamp
- `end_time` - Session end timestamp
- `total_events` - Number of events in session
- `total_watch_time` - Total watch time in seconds
- `created_at` - Record creation timestamp

### Events Table
- `id` - Primary key
- `session_id` - Foreign key to session
- `reel_id` - Instagram reel identifier
- `username` - Content creator username
- `caption` - Reel caption text
- `liked` - Whether user liked the reel
- `watch_time` - Time spent watching (seconds)
- `replay_count` - Number of replays
- `scroll_speed` - Scroll speed metric
- `timestamp` - Event timestamp
- `created_at` - Record creation timestamp

## 🔧 Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Neon** - Serverless PostgreSQL database
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

## 🔒 CORS Configuration

CORS is configured to allow requests from:
- Dashboard: `http://localhost:5173`
- Chrome Extension: `chrome-extension://*`

Modify `CORS_ORIGINS` in `.env` to add more origins.
