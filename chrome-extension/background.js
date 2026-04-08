// AIMirror Background Service Worker
// Handles data batching, storage management, and communication with backend

console.log('[AIMirror Background] Service worker loaded');

// Configuration
const CONFIG = {
  BACKEND_URL: 'http://localhost:8000/ingest',
  SYNC_INTERVAL: 30000, // Sync every 30 seconds
  MAX_STORAGE_EVENTS: 1000 // Maximum events to keep in storage
};

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
