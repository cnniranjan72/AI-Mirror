# AIMirror Chrome Extension

Manifest V3 Chrome extension for tracking Instagram Reels behavioral data.

## 🚀 Installation

### 1. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right corner)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder

### 2. Verify Installation

- You should see the AIMirror extension icon in your toolbar
- Click the icon to open the popup and check status

### 3. Configure Backend URL (Optional)

If your backend is not running on `http://localhost:3000`, edit `content.js`:

```javascript
const CONFIG = {
  BACKEND_URL: 'http://your-backend-url:port/api/events'
};
```

## 📋 Features

### Automatic Tracking
- ✅ Detects Instagram Reels automatically
- ✅ Tracks watch time per reel
- ✅ Monitors like interactions
- ✅ Records scroll behavior
- ✅ Counts replay events

### Data Collection
- **Reel ID** - Unique identifier for each reel
- **Username** - Content creator
- **Caption** - Reel description (truncated)
- **Liked** - Whether you liked the reel
- **Watch Time** - Seconds spent watching
- **Replay Count** - Number of times rewatched
- **Scroll Speed** - Scrolling intensity (px/s)
- **Timestamp** - When the event occurred

### Privacy & Storage
- All data stored locally in `chrome.storage.local`
- Batched sync to backend every 60 seconds
- No data sent without your consent
- Clear data anytime from popup

## 🔧 How It Works

### Content Script (`content.js`)
- Runs on `instagram.com/*`
- Uses `IntersectionObserver` to detect visible reels
- Uses `MutationObserver` to detect new reels
- Tracks user interactions (likes, scrolls)
- Monitors tab visibility for accurate watch time

### Background Service Worker (`background.js`)
- Manages data synchronization
- Handles periodic syncing (60s intervals)
- Cleans up old data when storage limit reached
- Communicates with popup UI

### Popup UI
- Shows current tracking status
- Displays session and event counts
- Manual sync button
- Link to dashboard
- Clear data option

## 📊 Data Flow

```
Instagram Page
    ↓
Content Script (observes behavior)
    ↓
chrome.storage.local (temporary storage)
    ↓
Background Worker (batches data)
    ↓
Backend API (persistent storage)
    ↓
Dashboard (visualization)
```

## ⚙️ Configuration

Edit `content.js` to customize:

```javascript
const CONFIG = {
  BATCH_INTERVAL: 60000,        // Sync interval (ms)
  MIN_WATCH_TIME: 0.5,          // Minimum watch time to record (s)
  BACKEND_URL: 'http://...'     // Backend API endpoint
};
```

## 🐛 Debugging

### View Console Logs

1. Right-click extension icon → "Inspect popup" (for popup logs)
2. Open Instagram → F12 → Console (for content script logs)
3. `chrome://extensions/` → "Inspect views: service worker" (for background logs)

### Check Storage

```javascript
// In console
chrome.storage.local.get(['sessions'], (result) => {
  console.log(result);
});
```

## 🔒 Privacy & Ethics

- **No Scraping** - Only observes visible DOM elements
- **Consent-Based** - User must install and enable
- **Local-First** - Data stored locally before sync
- **Transparent** - All code is open source
- **No External Services** - Only syncs to your backend

## ⚠️ Limitations

- Only works on Instagram Reels (not posts or stories)
- Requires active tab for accurate tracking
- May not capture all interactions if DOM changes
- Depends on Instagram's current DOM structure

## 🔄 Updates

After making changes to the extension:

1. Go to `chrome://extensions/`
2. Click the refresh icon on the AIMirror extension
3. Reload Instagram page

## 📝 Icons

The extension requires icons in the `icons/` folder:
- `icon16.png` - 16x16 pixels
- `icon48.png` - 48x48 pixels  
- `icon128.png` - 128x128 pixels

See `icons/README.md` for icon generation instructions.
