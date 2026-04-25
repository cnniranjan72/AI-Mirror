// AIMirror Content Script — Instagram Reels Behavioral Tracker
// Production-grade extraction with viewport detection + batched sending

(function () {
  'use strict';

  // ==================== CONFIGURATION ====================

  const CONFIG = {
    CHECK_INTERVAL: 1000,
    EXTRACT_DELAY: 1000,
    MIN_WATCH_TIME: 0.5,
    BATCH_SIZE: 10,
    BATCH_INTERVAL: 30000,
    BACKEND_URL: 'http://localhost:8000/ingest',
    USER_ID: 'default',
  };

  // ==================== STATE ====================

  const state = {
    currentVideo: null,
    currentReelId: null,
    startTime: null,
    sessionId: `sess_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`,
    buffer: [],
    lastBatchTime: Date.now(),
    extractionPending: false,
  };

  console.log('[AIMirror] Content script loaded — session:', state.sessionId);

  // ==================== UTILITIES ====================

  function reelIdFromUrl() {
    const m = window.location.pathname.match(/\/reel\/([A-Za-z0-9_-]+)/);
    return m ? m[1] : `reel_${Date.now().toString(36)}`;
  }

  // ==================== METADATA EXTRACTION ====================

  function extractMetadata(video) {
    const container = video.closest('[role="presentation"]')
      || video.closest('article')
      || video.parentElement?.parentElement?.parentElement;

    let username = 'unknown';
    let caption = '';
    let hashtags = [];
    let audio = '';

    if (!container) {
      return { username, caption, hashtags, audio };
    }

    // --- Username ---
    try {
      const link = container.querySelector('a[href*="/reels/"] span');
      if (link && link.textContent) {
        username = link.textContent.trim();
      }
      if (username === 'unknown') {
        const profileLink = container.querySelector('a[href*="/reels/"]');
        if (profileLink) {
          const href = profileLink.getAttribute('href') || '';
          const parts = href.split('/').filter(Boolean);
          if (parts.length >= 1 && parts[0] !== 'reels') {
            username = parts[0];
          }
        }
      }
    } catch (e) {
      console.warn('[AIMirror] Username extraction error:', e.message);
    }

    // --- Caption ---
    try {
      const candidates = container.querySelectorAll('div[role="button"] span');
      for (const el of candidates) {
        const txt = (el.innerText || '').trim();
        if (
          txt.length > 10 &&
          txt.split(/\s+/).length >= 3 &&
          !/^\d+$/.test(txt) &&
          txt.toLowerCase() !== username.toLowerCase()
        ) {
          caption = txt;
          break;
        }
      }
    } catch (e) {
      console.warn('[AIMirror] Caption extraction error:', e.message);
    }

    // --- Hashtags (regex from caption) ---
    if (caption) {
      const matches = caption.match(/#[a-zA-Z0-9_]+/g);
      if (matches) hashtags = matches;
    }

    // --- Audio ---
    try {
      const audioLink = container.querySelector('a[href*="/audio/"] span');
      if (audioLink) {
        audio = (audioLink.textContent || '').trim();
      }
    } catch (_) { /* optional */ }

    return { username, caption, hashtags, audio };
  }

  // ==================== VIEWPORT DETECTION ====================

  function getActiveVideo() {
    const videos = document.querySelectorAll('video');
    let best = null;
    let maxArea = 0;

    videos.forEach((video) => {
      const r = video.getBoundingClientRect();
      const vH = Math.min(r.bottom, window.innerHeight) - Math.max(r.top, 0);
      const vW = Math.min(r.right, window.innerWidth) - Math.max(r.left, 0);
      const area = Math.max(0, vH) * Math.max(0, vW);
      if (area > maxArea) {
        maxArea = area;
        best = video;
      }
    });

    return best;
  }

  // ==================== WATCH SESSION ====================

  function startWatching(video) {
    state.currentVideo = video;
    state.currentReelId = reelIdFromUrl();
    state.startTime = Date.now();
    state.extractionPending = true;
    console.log('[AIMirror] ▶ Watching:', state.currentReelId);
  }

  function stopWatching() {
    if (!state.currentVideo || !state.startTime) return;

    const watchTime = (Date.now() - state.startTime) / 1000;

    if (watchTime >= CONFIG.MIN_WATCH_TIME) {
      const meta = extractMetadata(state.currentVideo);

      const event = {
        reel_id: state.currentReelId,
        username: meta.username,
        caption: meta.caption,
        hashtags: meta.hashtags,
        audio: meta.audio,
        watch_time: parseFloat(watchTime.toFixed(2)),
        timestamp: new Date().toISOString(),
        session_id: state.sessionId,
      };

      state.buffer.push(event);

      console.log('[AIMirror] ■ Stopped:', state.currentReelId,
        `(${watchTime.toFixed(1)}s)`, meta.username);

      checkBatch();
    }

    state.currentVideo = null;
    state.currentReelId = null;
    state.startTime = null;
    state.extractionPending = false;
  }

  function checkActiveVideo() {
    const active = getActiveVideo();

    if (!active) {
      if (state.currentVideo) stopWatching();
      return;
    }

    if (state.currentVideo === active) return;

    if (state.currentVideo) stopWatching();
    startWatching(active);
  }

  // ==================== BATCHING ====================

  function checkBatch() {
    const sizeReached = state.buffer.length >= CONFIG.BATCH_SIZE;
    const timeReached = Date.now() - state.lastBatchTime >= CONFIG.BATCH_INTERVAL;

    if (sizeReached || timeReached) {
      sendBatch();
    }
  }

  function sendBatch() {
    if (state.buffer.length === 0) return;

    const events = [...state.buffer];
    state.buffer = [];
    state.lastBatchTime = Date.now();

    const payload = {
      user_id: CONFIG.USER_ID,
      events: events,
    };

    console.log(`[AIMirror] → Sending ${events.length} events to backend`);

    fetch(CONFIG.BACKEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then((res) => res.json())
      .then((data) => {
        console.log('[AIMirror] ✓ Batch sent:', data.message || data);
      })
      .catch((err) => {
        console.error('[AIMirror] ✗ Send failed:', err.message);
        // Put events back in buffer for retry
        state.buffer = [...events, ...state.buffer];
      });
  }

  // ==================== INITIALIZATION ====================

  function initialize() {
    if (!window.location.hostname.includes('instagram.com')) {
      console.log('[AIMirror] Not Instagram — skipping');
      return;
    }

    console.log('[AIMirror] Initializing tracker...');

    // Active video check every 1s
    setInterval(checkActiveVideo, CONFIG.CHECK_INTERVAL);

    // Time-based batch check every 30s
    setInterval(() => {
      checkBatch();
    }, CONFIG.BATCH_INTERVAL);

    // Notify background script
    try {
      chrome.runtime.sendMessage({
        type: 'TRACKER_INITIALIZED',
        sessionId: state.sessionId,
      });
    } catch (_) { /* background not ready */ }

    console.log('[AIMirror] Tracker ready');
  }

  // ==================== CLEANUP ====================

  window.addEventListener('beforeunload', () => {
    if (state.currentVideo) stopWatching();
    if (state.buffer.length > 0) sendBatch();
  });

  // ==================== DEBUG ====================

  window.aimirrorDebug = function () {
    const active = getActiveVideo();
    const meta = active ? extractMetadata(active) : null;
    console.table({
      session: state.sessionId,
      currentReel: state.currentReelId || '(none)',
      watchingSince: state.startTime ? `${((Date.now() - state.startTime) / 1000).toFixed(1)}s` : '-',
      bufferSize: state.buffer.length,
      activeVideo: !!active,
    });
    if (meta) console.log('[AIMirror] Current metadata:', meta);
    return { state, meta };
  };

  // ==================== START ====================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }
})();
