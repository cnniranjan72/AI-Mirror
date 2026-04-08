// AIMirror Content Script - Instagram Reels Behavioral Tracker
// Robust active video detection with reliable watch session tracking

try {
  console.log("[AIMirror] SCRIPT START");
} catch (e) {
  console.error("Script crashed:", e);
}

(function() {
  'use strict';

  console.log('[AIMirror] Content script loaded on Instagram');

  // ==================== STATE MANAGEMENT ====================

  const state = {
    currentVideo: null,
    currentReelId: null,
    startTime: null,
    sessionId: generateSessionId(),
    events: [],
    eventBuffer: [],
    lastCheckTime: Date.now()
  };

  // ==================== CONFIGURATION ====================

  const CONFIG = {
    CHECK_INTERVAL: 1000,        // Check active video every 1 second
    MIN_WATCH_TIME: 0.5,         // Minimum watch time to record (seconds)
    BUFFER_SIZE: 10,             // Store events before saving
    BUFFER_TIME: 30000,          // Save buffer every 30 seconds
    BATCH_INTERVAL: 60000,       // Send to backend every 60 seconds
    BACKEND_URL: 'http://localhost:3000/api/events'
  };

  console.log('[AIMirror] Configuration loaded');

  // ==================== UTILITY FUNCTIONS ====================

  function generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  function generateReelId() {
    // Try to extract reel ID from URL
    const url = window.location.pathname;
    const match = url.match(/\/reel\/([A-Za-z0-9_-]+)/);
    if (match) return match[1];
    
    // Fallback: generate hash from timestamp + random
    const hash = Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    return `reel_${hash}`;
  }

  function extractUsername(video) {
    // Traverse DOM upward from video to find username link
    let el = video.closest('article') || video.parentElement;
    
    while (el && el !== document.body) {
      const link = el.querySelector('a[href^="/"]');
      if (link && link.innerText && link.innerText.length < 30 && link.innerText.length > 0) {
        const username = link.innerText.trim().replace('@', '');
        if (username && !username.includes(' ')) {
          return username;
        }
      }
      el = el.parentElement;
    }
    
    return 'unknown';
  }

  // ==================== ACTIVE VIDEO DETECTION ====================

  function getActiveVideo() {
    const videos = document.querySelectorAll('video');
    
    if (videos.length === 0) {
      return null;
    }

    let bestVideo = null;
    let maxVisibleArea = 0;

    videos.forEach(video => {
      const rect = video.getBoundingClientRect();

      // Calculate visible area in viewport
      const visibleHeight = Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0);
      const visibleWidth = Math.min(rect.right, window.innerWidth) - Math.max(rect.left, 0);

      const visibleArea = Math.max(0, visibleHeight) * Math.max(0, visibleWidth);

      if (visibleArea > maxVisibleArea) {
        maxVisibleArea = visibleArea;
        bestVideo = video;
      }
    });

    return bestVideo;
  }

  // ==================== WATCH SESSION TRACKING ====================

  function checkActiveVideo() {
    const activeVideo = getActiveVideo();
    const now = Date.now();

    // Log total videos detected
    const totalVideos = document.querySelectorAll('video').length;
    if (totalVideos > 0 && now - state.lastCheckTime > 5000) {
      console.log(`[AIMirror] Total videos detected: ${totalVideos}`);
      state.lastCheckTime = now;
    }

    // No active video found
    if (!activeVideo) {
      if (state.currentVideo) {
        stopWatching();
      }
      return;
    }

    // Same video still active
    if (state.currentVideo === activeVideo) {
      return;
    }

    // Video changed - stop previous and start new
    if (state.currentVideo) {
      console.log('[AIMirror] Active video changed');
      stopWatching();
    }

    startWatching(activeVideo);
  }

  function startWatching(video) {
    if (!video) return;

    state.currentVideo = video;
    state.currentReelId = generateReelId();
    state.startTime = Date.now();

    console.log('[AIMirror] Started watching reel:', state.currentReelId);
    console.log('[AIMirror] Active video detected');
  }

  function stopWatching() {
    if (!state.currentVideo || !state.startTime) return;

    const watchTime = (Date.now() - state.startTime) / 1000; // Convert to seconds

    // Only record if watch time meets minimum threshold
    if (watchTime >= CONFIG.MIN_WATCH_TIME) {
      const username = extractUsername(state.currentVideo);
      
      const event = {
        reel_id: state.currentReelId,
        username: username,
        watch_time: parseFloat(watchTime.toFixed(2)),
        timestamp: new Date().toISOString(),
        session_id: state.sessionId
      };

      state.eventBuffer.push(event);
      console.log('[AIMirror] Stopped watching reel:', state.currentReelId);
      console.log('[AIMirror] Event recorded:', event);

      // Save buffer if needed
      saveBufferIfNeeded();
    }

    // Reset state
    state.currentVideo = null;
    state.currentReelId = null;
    state.startTime = null;
  }

  // ==================== EVENT PIPELINE ====================

  function saveBufferIfNeeded() {
    // Save to chrome.storage if buffer is full or time threshold reached
    if (state.eventBuffer.length >= CONFIG.BUFFER_SIZE) {
      saveToStorage();
    }
  }

  function saveToStorage() {
    if (state.eventBuffer.length === 0) return;

    chrome.storage.local.get(['events'], (result) => {
      const storedEvents = result.events || [];
      const allEvents = [...storedEvents, ...state.eventBuffer];

      chrome.storage.local.set({ events: allEvents }, () => {
        console.log(`[AIMirror] Saved ${state.eventBuffer.length} events to storage (total: ${allEvents.length})`);
        state.eventBuffer = [];
      });
    });
  }

  // ==================== BATCH SENDING ====================

  function sendBatchToBackend() {
    chrome.storage.local.get(['events'], (result) => {
      const events = result.events || [];

      if (events.length === 0) {
        return;
      }

      const sessionData = {
        session_id: state.sessionId,
        start_time: new Date().toISOString(),
        end_time: new Date().toISOString(),
        events: events
      };

      fetch(CONFIG.BACKEND_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(sessionData)
      })
        .then(response => response.json())
        .then(data => {
          console.log(`[AIMirror] Batch sent: ${events.length} events`);
          // Clear sent events from storage
          chrome.storage.local.set({ events: [] });
        })
        .catch(error => {
          console.error('[AIMirror] Failed to send batch:', error);
        });
    });
  }

  // ==================== INITIALIZATION ====================

  function initialize() {
    console.log('[AIMirror] Initializing behavioral tracker...');

    // Check if we're on Instagram
    if (!window.location.hostname.includes('instagram.com')) {
      console.log('[AIMirror] Not on Instagram, skipping initialization');
      return;
    }

    // Start checking for active video every second
    setInterval(checkActiveVideo, CONFIG.CHECK_INTERVAL);

    // Save buffer periodically
    setInterval(saveToStorage, CONFIG.BUFFER_TIME);

    // Send batch to backend periodically
    setInterval(sendBatchToBackend, CONFIG.BATCH_INTERVAL);

    console.log('[AIMirror] Behavioral tracker initialized successfully');
    console.log('[AIMirror] Checking for active videos every', CONFIG.CHECK_INTERVAL, 'ms');

    // Send message to background script
    chrome.runtime.sendMessage({
      type: 'TRACKER_INITIALIZED',
      sessionId: state.sessionId
    }).catch(() => {
      // Ignore if background script not ready
    });
  }

  // ==================== CLEANUP ====================

  window.addEventListener('beforeunload', () => {
    if (state.currentVideo) {
      stopWatching();
    }
    saveToStorage();
  });

  // ==================== MANUAL TEST FUNCTION ====================

  window.testAIMirror = function() {
    console.log('[AIMirror] === Manual Test Started ===');
    
    console.log('[AIMirror] Current URL:', window.location.href);
    console.log('[AIMirror] Hostname:', window.location.hostname);
    
    const videos = document.querySelectorAll('video');
    console.log(`[AIMirror] Total videos found: ${videos.length}`);
    
    const activeVideo = getActiveVideo();
    console.log('[AIMirror] Active video:', activeVideo);
    
    if (activeVideo) {
      const rect = activeVideo.getBoundingClientRect();
      console.log('[AIMirror] Active video position:', rect);
      console.log('[AIMirror] Active video visible area:', 
        (Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0)) *
        (Math.min(rect.right, window.innerWidth) - Math.max(rect.left, 0))
      );
    }
    
    console.log('[AIMirror] Current state:', {
      currentVideo: state.currentVideo,
      currentReelId: state.currentReelId,
      startTime: state.startTime,
      eventBuffer: state.eventBuffer.length,
      sessionId: state.sessionId
    });
    
    console.log('[AIMirror] === Manual Test Complete ===');
  };

  // ==================== START ====================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }

  // ==================== HEARTBEAT & DETECTION LOOP ====================

  // Heartbeat to verify script is running
  setInterval(() => {
    console.log("[AIMirror] HEARTBEAT RUNNING");
  }, 3000);

  // Main detection loop
  setInterval(() => {
    const videos = document.querySelectorAll("video");

    console.log("[AIMirror] Videos found:", videos.length);

    if (videos.length === 0) return;

    let bestVideo = null;
    let maxVisibleArea = 0;

    videos.forEach(video => {
      const rect = video.getBoundingClientRect();

      const visibleHeight = Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0);
      const visibleWidth = Math.min(rect.right, window.innerWidth) - Math.max(rect.left, 0);

      const visibleArea = Math.max(0, visibleHeight) * Math.max(0, visibleWidth);

      if (visibleArea > maxVisibleArea) {
        maxVisibleArea = visibleArea;
        bestVideo = video;
      }
    });

    if (bestVideo) {
      console.log("[AIMirror] ACTIVE VIDEO DETECTED", {
        time: bestVideo.currentTime,
        paused: bestVideo.paused
      });
    }

  }, 2000);

})();
