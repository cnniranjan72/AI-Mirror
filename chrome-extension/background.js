// AIMirror Background Service Worker
// Handles data batching, storage management, and communication with backend

console.log('[AIMirror Background] Service worker loaded');

// Configuration
const CONFIG = {
  BACKEND_URL: 'http://localhost:3000/api/events',
  SYNC_INTERVAL: 60000, // Sync every 60 seconds
  MAX_STORAGE_EVENTS: 1000 // Maximum events to keep in storage
};

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

    case 'GET_SESSION_INFO':
      getSessionInfo().then(sendResponse);
      return true; // Keep channel open for async response

    case 'SYNC_NOW':
      syncDataToBackend().then(sendResponse);
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

// ==================== DATA SYNC ====================

async function syncDataToBackend() {
  try {
    const result = await chrome.storage.local.get(['sessions']);
    const sessions = result.sessions || [];

    if (sessions.length === 0) {
      console.log('[AIMirror Background] No sessions to sync');
      return { success: true, synced: 0 };
    }

    let syncedCount = 0;
    const errors = [];

    for (const session of sessions) {
      if (session.events && session.events.length > 0) {
        try {
          const response = await fetch(CONFIG.BACKEND_URL, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(session)
          });

          if (response.ok) {
            syncedCount++;
            console.log(`[AIMirror Background] Synced session ${session.session_id}`);
          } else {
            errors.push(`Session ${session.session_id}: ${response.statusText}`);
          }
        } catch (error) {
          errors.push(`Session ${session.session_id}: ${error.message}`);
          console.error('[AIMirror Background] Sync error:', error);
        }
      }
    }

    // If all sessions synced successfully, clear them from storage
    if (syncedCount === sessions.length && errors.length === 0) {
      await chrome.storage.local.set({ sessions: [] });
      console.log('[AIMirror Background] Cleared synced sessions from storage');
    }

    return {
      success: errors.length === 0,
      synced: syncedCount,
      errors: errors
    };

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
