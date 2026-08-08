// AIMirror Background Service Worker
// Handles data batching, storage management, and communication with backend

console.log('[AIMirror Background] Service worker loaded');

// Configuration
// Points at the deployed backend by default so the extension works out of
// the box for real users — override via the Options page
// (chrome.storage.local.backendUrl) if you're running the backend locally
// yourself instead (http://localhost:8000).
const DEFAULT_BACKEND_URL = 'https://aimirror-backend-cu00.onrender.com';

const CONFIG = {
  BACKEND_URL: `${DEFAULT_BACKEND_URL}/ingest`,
  API_BASE_URL: DEFAULT_BACKEND_URL,
  SYNC_INTERVAL: 30000, // Sync every 30 seconds
  MAX_STORAGE_EVENTS: 1000 // Maximum events to keep in storage
};

function applyBackendUrl(url) {
  if (!url) return;
  CONFIG.API_BASE_URL = url;
  CONFIG.BACKEND_URL = `${url}/ingest`;
  console.log('[AIMirror Background] Using configured backend URL:', url);
}

chrome.storage.local.get(['backendUrl'], (result) => applyBackendUrl(result.backendUrl));

// Picks up a change made on the Options page while this service worker is
// already running, without needing the extension reloaded.
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.backendUrl) applyBackendUrl(changes.backendUrl.newValue);
});

// User ID management
let userId = null;

// Initialize user ID on startup
chrome.storage.local.get(['userId'], (result) => {
  if (!result.userId) {
    userId = 'user_' + Math.random().toString(36).substr(2, 9);
    chrome.storage.local.set({ userId });
    console.log('[AIMirror Background] Generated user ID:', userId);
  } else {
    userId = result.userId;
    console.log('[AIMirror Background] Loaded user ID:', userId);
  }
});

// State
let activeSessions = new Map();

// ==================== MESSAGE HANDLING ====================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[AIMirror Background] Received message:', message.type);

  switch (message.type) {
    case 'TRACKER_INITIALIZED':
      handleTrackerInitialized(message, sender);
      sendResponse({ success: true });
      break;

    case 'SEND_EVENTS':
      // Content scripts can't fetch our backend directly (blocked by
      // Instagram's page CSP). The background worker fetches instead — its
      // requests use the extension host_permissions, not the page CSP.
      sendEventsToBackend(message.payload).then(sendResponse);
      return true; // async response

    case 'GET_SESSION_INFO':
      getSessionInfo().then(sendResponse);
      return true; // Keep channel open for async response

    case 'SYNC_NOW':
      syncDataToBackend().then(sendResponse);
      return true;

    case 'GET_BACKEND_STATUS':
      getBackendStatus(sender.tab?.id).then(sendResponse);
      return true;

    case 'CLEAR_DATA':
      clearAllData().then(sendResponse);
      return true;

    default:
      sendResponse({ success: false, error: 'Unknown message type' });
  }
});

// ==================== SESSION MANAGEMENT ====================

function handleTrackerInitialized(message, sender) {
  const tabId = sender.tab?.id;
  if (tabId) {
    activeSessions.set(tabId, {
      sessionId: message.sessionId,
      startTime: Date.now(),
      tabId: tabId
    });
    console.log(`[AIMirror Background] Tracker initialized for tab ${tabId}`);
  }
}

async function getSessionInfo() {
  const result = await chrome.storage.local.get(['sessions']);
  const sessions = result.sessions || [];
  
  return {
    success: true,
    totalSessions: sessions.length,
    totalEvents: sessions.reduce((sum, s) => sum + (s.events?.length || 0), 0),
    activeSessions: activeSessions.size
  };
}

async function getBackendStatus(activeTabId) {
  const result = await chrome.storage.local.get(['sessions', 'userId']);
  const userId = result.userId || 'default';
  const sessions = result.sessions || [];
  const localEvents = sessions.reduce((sum, s) => sum + (s.events?.length || 0), 0);
  // Tracks Instagram AND YouTube sessions now — name reflects that.
  const isTracking = activeTabId ? activeSessions.has(activeTabId) : false;

  const status = {
    connected: false,
    persona: null,
    backendEvents: 0,
    identityConfidence: null,
    identityVersion: null,
    synced: false,
  };

  try {
    const healthResp = await fetch(`${CONFIG.API_BASE_URL}/health`, { signal: AbortSignal.timeout(5000) });
    if (!healthResp.ok) return { ...status, localEvents, isTracking, activeSessions: activeSessions.size };
    status.connected = true;

    const [summaryResp, profileResp] = await Promise.allSettled([
      fetch(`${CONFIG.API_BASE_URL}/cognitive/summary?user_id=${userId}`, { signal: AbortSignal.timeout(5000) }),
      fetch(`${CONFIG.API_BASE_URL}/profile?user_id=${userId}`, { signal: AbortSignal.timeout(5000) }),
    ]);

    if (summaryResp.status === 'fulfilled' && summaryResp.value.ok) {
      const summary = await summaryResp.value.json();
      status.backendEvents = summary.evidence_count || 0;
      status.identityVersion = summary.current_identity?.identity_version || null;
      status.identityConfidence = summary.current_identity?.overall_confidence || null;
    }

    if (profileResp.status === 'fulfilled' && profileResp.value.ok) {
      const profile = await profileResp.value.json();
      if (profile.persona_label && profile.persona_label !== 'No Data') {
        status.persona = {
          label: profile.persona_label,
          confidence: profile.confidence,
          traits: profile.traits || {},
        };
      }
    }

    status.synced = true;
  } catch (_) {
    // Backend unreachable — status.connected stays false
  }

  return { ...status, localEvents, isTracking, activeSessions: activeSessions.size };
}

// ==================== DATA SYNC ====================

// Receives a batch from the content script and POSTs it to the backend.
// Runs in the extension (background) context, so it bypasses the host page's
// Content-Security-Policy that blocks direct content-script fetches.
async function sendEventsToBackend(payload) {
  try {
    const response = await fetch(CONFIG.BACKEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const text = await response.text();
      console.error('[AIMirror Background] Backend error:', response.status, text);
      return { success: false, error: `Backend ${response.status}: ${text}` };
    }
    const data = await response.json();
    console.log(`[AIMirror Background] ✓ Sent ${payload.events?.length || 0} events:`, data);
    if (payload.warnings && payload.warnings.length > 0) {
      await recordExtractionWarnings(payload.warnings.length);
    }
    return { success: true, data };
  } catch (error) {
    console.error('[AIMirror Background] Send error:', error);
    return { success: false, error: error.message };
  }
}

// Tracked so the popup can show "N items couldn't be read this session"
// instead of extraction failures being invisible (console-only) the way
// they were before — this is exactly the failure mode that let the
// "untitled" caption bug go unnoticed.
async function recordExtractionWarnings(count) {
  try {
    const { extractionFailureCount = 0 } = await chrome.storage.local.get(['extractionFailureCount']);
    await chrome.storage.local.set({ extractionFailureCount: extractionFailureCount + count });
  } catch (err) {
    console.warn('[AIMirror Background] Could not record extraction warning count:', err.message);
  }
}

async function syncDataToBackend() {
  try {
    const result = await chrome.storage.local.get(['sessions']);
    const sessions = result.sessions || [];

    if (sessions.length === 0) {
      console.log('[AIMirror Background] No sessions to sync');
      return { success: true, synced: 0 };
    }

    // Collect all events from all sessions
    const allEvents = [];
    for (const session of sessions) {
      if (session.events && session.events.length > 0) {
        allEvents.push(...session.events);
      }
    }

    if (allEvents.length === 0) {
      console.log('[AIMirror Background] No events to sync');
      return { success: true, synced: 0 };
    }

    try {
      // Send all events in single batch to new backend format
      const response = await fetch(CONFIG.BACKEND_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          events: allEvents
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log(`[AIMirror Background] Synced ${allEvents.length} events:`, data);
        
        // Clear synced sessions from storage
        await chrome.storage.local.set({ sessions: [] });
        console.log('[AIMirror Background] Cleared synced sessions from storage');
        
        return {
          success: true,
          synced: allEvents.length,
          response: data
        };
      } else {
        const errorText = await response.text();
        console.error('[AIMirror Background] Backend error:', response.status, errorText);
        return {
          success: false,
          error: `Backend error: ${response.status} ${errorText}`
        };
      }
    } catch (error) {
      console.error('[AIMirror Background] Sync error:', error);
      return {
        success: false,
        error: error.message
      };
    }

  } catch (error) {
    console.error('[AIMirror Background] Sync failed:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// ==================== STORAGE MANAGEMENT ====================

async function clearAllData() {
  try {
    await chrome.storage.local.clear();
    activeSessions.clear();
    console.log('[AIMirror Background] All data cleared');
    return { success: true };
  } catch (error) {
    console.error('[AIMirror Background] Clear data failed:', error);
    return { success: false, error: error.message };
  }
}

async function cleanupOldData() {
  try {
    const result = await chrome.storage.local.get(['sessions']);
    const sessions = result.sessions || [];

    // Count total events
    const totalEvents = sessions.reduce((sum, s) => sum + (s.events?.length || 0), 0);

    if (totalEvents > CONFIG.MAX_STORAGE_EVENTS) {
      console.log(`[AIMirror Background] Storage limit reached (${totalEvents} events), triggering sync`);
      await syncDataToBackend();
    }
  } catch (error) {
    console.error('[AIMirror Background] Cleanup failed:', error);
  }
}

// ==================== PERIODIC SYNC ====================

// Set up periodic sync
setInterval(() => {
  console.log('[AIMirror Background] Running periodic sync...');
  syncDataToBackend();
  cleanupOldData();
}, CONFIG.SYNC_INTERVAL);

// ==================== TAB MANAGEMENT ====================

chrome.tabs.onRemoved.addListener((tabId) => {
  if (activeSessions.has(tabId)) {
    console.log(`[AIMirror Background] Tab ${tabId} closed, removing session`);
    activeSessions.delete(tabId);
  }
});

// ==================== INSTALLATION ====================

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('[AIMirror Background] Extension installed');
    
    // Set default configuration
    chrome.storage.local.set({
      sessions: [],
      config: {
        backendUrl: CONFIG.BACKEND_URL,
        syncInterval: CONFIG.SYNC_INTERVAL
      }
    });
  } else if (details.reason === 'update') {
    console.log('[AIMirror Background] Extension updated');
  }
});

console.log('[AIMirror Background] Service worker initialized');
