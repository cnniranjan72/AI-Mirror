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
    // Backend runs on :8001 in local dev (:8000 is taken by another service).
    // Change the port here (and in background.js) to match your backend.
    BACKEND_URL: 'http://localhost:8001/ingest',
    // The twin this data feeds. Matches the dashboard's default user
    // (VITE_USER_ID) so watched reels evolve the twin you see in the UI.
    USER_ID: 'test_user_001',
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

  // Instagram renders the <video> and its metadata (username, caption) in
  // SEPARATE sibling subtrees, and the action rail (like/save/audio) in yet
  // another. So we can't rely on closest('[role=presentation]') or a fixed
  // number of parents. Instead, walk UP from the video until we reach the
  // smallest ancestor that contains BOTH a profile/reels link AND an action
  // control — that ancestor is the whole reel "card".
  function findReelCard(video) {
    let el = video.parentElement;
    for (let i = 0; i < 15 && el; i++) {
      try {
        const hasLink = el.querySelector('a[href*="/reels/"], a[href*="/audio/"]');
        const hasAction = el.querySelector(
          'svg[aria-label="Like"], svg[aria-label="Unlike"], a[href*="/audio/"]'
        );
        if (hasLink && hasAction) return el;
      } catch (_) { /* keep walking */ }
      el = el.parentElement;
    }
    // Fallback: broadest reasonable ancestor.
    return video.closest('article')
      || video.parentElement?.parentElement?.parentElement
      || document.body;
  }

  function extractMetadata(video) {
    const card = findReelCard(video);

    let username = 'unknown';
    let caption = '';
    let hashtags = [];
    let audioInfo = '';
    let audioId = '';
    let liked = false;
    let saved = false;
    let following = true;
    let profileUrl = '';

    if (!card) {
      return { username, caption, hashtags, audioInfo, audioId, liked, saved, following, profileUrl };
    }

    // --- Username: from the profile link href (stable across redesigns) ---
    try {
      const links = card.querySelectorAll('a[href*="/reels/"]');
      for (const a of links) {
        const parts = (a.getAttribute('href') || '').split('/').filter(Boolean);
        if (parts.length && !['reels', 'reel', 'explore', 'p'].includes(parts[0])) {
          username = parts[0];
          break;
        }
      }
      if (username !== 'unknown') profileUrl = `https://instagram.com/${username}`;
    } catch (e) {
      console.warn('[AIMirror] Username extraction error:', e.message);
    }

    // --- Caption: the dir="auto" text block, minus a trailing "… more" ---
    try {
      const blocks = card.querySelectorAll('div[dir="auto"]');
      for (const d of blocks) {
        const spans = d.querySelectorAll('span');
        let text = '';
        spans.forEach((s) => {
          const t = (s.innerText || '').trim();
          if (!t || /^(…?\s*more)$/i.test(t)) return;
          text = text ? `${text} ${t}` : t;
        });
        if (!text) text = (d.innerText || '').replace(/…?\s*more$/i, '').trim();
        if (text.length > 3 && text.toLowerCase() !== username.toLowerCase()) {
          caption = text;
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

    // --- Audio: the audio link href → id (no text span in current DOM) ---
    try {
      const audioLink = card.querySelector('a[href*="/audio/"]');
      if (audioLink) {
        const href = audioLink.getAttribute('href') || '';
        const m = href.match(/\/audio\/(\d+)/);
        if (m) audioId = m[1];
        // Prefer a text label if one exists, else fall back to the id.
        const span = audioLink.querySelector('span');
        audioInfo = (span && span.textContent.trim()) || (audioId ? `audio_${audioId}` : '');
      }
    } catch (_) { /* optional */ }

    // --- Engagement state (net-new signal) ---
    try {
      liked = !!card.querySelector('svg[aria-label="Unlike"]');
      saved = !!card.querySelector('svg[aria-label="Remove"]');
      // A visible "Follow" button means we do NOT follow this creator.
      const followBtn = Array.from(card.querySelectorAll('div[role="button"]'))
        .find((b) => (b.textContent || '').trim() === 'Follow');
      following = !followBtn;
    } catch (_) { /* optional */ }

    return { username, caption, hashtags, audioInfo, audioId, liked, saved, following, profileUrl };
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
        // Backend normalizer reads `audio_info` (not `audio`).
        audio_info: meta.audioInfo,
        audio_id: meta.audioId,
        watch_time: parseFloat(watchTime.toFixed(2)),
        // Engagement signal now captured from the DOM.
        liked: meta.liked,
        saved: meta.saved,
        following: meta.following,
        profile_url: meta.profileUrl,
        source_url: window.location.href,
        timestamp: new Date().toISOString(),
        session_id: state.sessionId,
      };

      state.buffer.push(event);

      console.log('[AIMirror] ■ Stopped:', state.currentReelId,
        `(${watchTime.toFixed(1)}s)`, meta.username,
        `liked=${meta.liked} saved=${meta.saved}`);

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

  // Run `aimirrorDebug()` in the Instagram tab's console to see exactly what
  // the extractor reads from the currently-visible reel.
  window.aimirrorDebug = function () {
    const active = getActiveVideo();
    const meta = active ? extractMetadata(active) : null;
    console.table({
      session: state.sessionId,
      currentReel: state.currentReelId || '(none)',
      watchingSince: state.startTime ? `${((Date.now() - state.startTime) / 1000).toFixed(1)}s` : '-',
      bufferSize: state.buffer.length,
      activeVideo: !!active,
      backend: CONFIG.BACKEND_URL,
    });
    if (meta) console.table(meta);
    return { state, meta };
  };

  // ==================== START ====================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }
})();
