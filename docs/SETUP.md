# AIMirror - Complete Setup Guide

Step-by-step guide to get AIMirror running on your machine.

## 📋 Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 16+** (for dashboard)
- **Chrome Browser** (for extension)
- **Neon Account** (free tier available)

## 🗄️ Step 1: Setup Neon Database

### 1.1 Create Neon Account

1. Go to https://console.neon.tech/
2. Sign up for a free account
3. Create a new project

### 1.2 Get Database URL

1. In your Neon project dashboard, click "Connection Details"
2. Copy the connection string (looks like):
   ```
   postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

## 🔧 Step 2: Setup Backend

### 2.1 Navigate to Backend

```bash
cd backend
```

### 2.2 Create Virtual Environment (Recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2.3 Install Dependencies

```bash
pip install -r requirements.txt
```

### 2.4 Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Neon database URL:

```env
DATABASE_URL=postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
PORT=3000
HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5173,chrome-extension://*
```

### 2.5 Run Backend

```bash
python main.py
```

You should see:
```
🚀 Starting AIMirror Backend API...
✅ Database tables created successfully
✅ API ready to receive requests
```

**Test it:** Open http://localhost:3000/docs to see the API documentation.

## 🎨 Step 3: Setup Dashboard

### 3.1 Open New Terminal

Keep the backend running and open a new terminal.

### 3.2 Navigate to Dashboard

```bash
cd dashboard
```

### 3.3 Install Dependencies

```bash
npm install
```

### 3.4 Run Dashboard

```bash
npm run dev
```

You should see:
```
VITE v5.0.11  ready in 500 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

**Test it:** Open http://localhost:5173 in your browser.

## 🔌 Step 4: Install Chrome Extension

### 4.1 Open Chrome Extensions

1. Open Chrome browser
2. Navigate to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top-right)

### 4.2 Load Extension

1. Click "Load unpacked"
2. Navigate to your project folder
3. Select the `chrome-extension` folder
4. Click "Select Folder"

### 4.3 Verify Installation

- You should see "AIMirror - Instagram Behavioral Tracker" in your extensions list
- The extension icon should appear in your toolbar
- Click the icon to open the popup

### 4.4 Add Extension Icons (Optional)

The extension works without icons, but you can add them:

1. Create or download 16x16, 48x48, and 128x128 pixel PNG images
2. Save them as `icon16.png`, `icon48.png`, `icon128.png`
3. Place them in `chrome-extension/icons/`
4. Reload the extension

## ✅ Step 5: Test the System

### 5.1 Test Backend

```bash
curl http://localhost:3000/health
```

Should return:
```json
{"status":"healthy","timestamp":"2026-04-08T..."}
```

### 5.2 Test Dashboard

1. Open http://localhost:5173
2. You should see the Overview page
3. It will show "No Data Yet" (this is normal)

### 5.3 Test Extension

1. Open Instagram in Chrome: https://www.instagram.com/
2. Navigate to Reels (or any reel link)
3. Open browser console (F12)
4. You should see logs like:
   ```
   [AIMirror] Content script loaded on Instagram
   [AIMirror] Initializing behavioral tracker...
   [AIMirror] Behavioral tracker initialized successfully
   ```

### 5.4 Generate Test Data

1. Watch a few Instagram Reels
2. Like some reels
3. Scroll through multiple reels
4. Wait 60 seconds for auto-sync (or click "Sync Now" in extension popup)
5. Refresh the dashboard to see your data

## 🎯 Step 6: Verify Data Flow

### 6.1 Check Extension Storage

1. Click the extension icon
2. You should see session and event counts
3. Status should show "Tracking active"

### 6.2 Check Backend

Visit http://localhost:3000/api/analytics

You should see JSON with your statistics.

### 6.3 Check Dashboard

1. Go to http://localhost:5173
2. Navigate to "Sessions" page
3. You should see your tracking sessions
4. Click on a session to view details

## 🔧 Troubleshooting

### Backend Issues

**Error: DATABASE_URL not set**
- Make sure you created `.env` file in `backend/` folder
- Verify the DATABASE_URL is correct

**Error: Connection refused**
- Check if Neon database is accessible
- Verify your internet connection
- Try the connection string in a PostgreSQL client

### Dashboard Issues

**Blank page or errors**
- Check browser console for errors (F12)
- Make sure backend is running on port 3000
- Try clearing browser cache

**"Failed to load analytics"**
- Verify backend is running: http://localhost:3000/health
- Check CORS settings in backend `.env`

### Extension Issues

**No logs in console**
- Make sure you're on instagram.com
- Reload the page after installing extension
- Check if extension is enabled in chrome://extensions/

**Data not syncing**
- Check extension popup for errors
- Verify backend URL in `content.js` (line 16)
- Check browser console for network errors

**"Tracking not active"**
- Navigate to Instagram Reels specifically
- Make sure you're on a reel page (URL contains `/reel/`)

## 🚀 Production Deployment

### Backend Deployment

Deploy to:
- **Railway** - https://railway.app/
- **Render** - https://render.com/
- **Fly.io** - https://fly.io/

Update `DATABASE_URL` to use your production Neon database.

### Dashboard Deployment

Deploy to:
- **Vercel** - https://vercel.com/
- **Netlify** - https://netlify.com/
- **Cloudflare Pages** - https://pages.cloudflare.com/

Update `VITE_API_URL` to point to your production backend.

### Extension

For production use:
1. Update `BACKEND_URL` in `content.js` to production API
2. Create proper icons
3. Package extension as `.crx` or publish to Chrome Web Store

## 📚 Next Steps

1. **Customize tracking** - Edit `content.js` to track additional metrics
2. **Add features** - Extend dashboard with new visualizations
3. **Improve accuracy** - Fine-tune detection algorithms
4. **Add authentication** - Secure your backend API
5. **Export data** - Add CSV/JSON export functionality

## 🆘 Getting Help

- Check the README files in each folder
- Review the code comments
- Check browser/terminal console for errors
- Verify all services are running

## 📝 Summary

After setup, you should have:

✅ Backend running on http://localhost:3000
✅ Dashboard running on http://localhost:5173  
✅ Extension installed and active in Chrome
✅ Data flowing: Extension → Backend → Dashboard

Happy tracking! 🪞
