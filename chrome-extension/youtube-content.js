// AIMirror Content Script — YouTube Watch + Shorts Behavioral Tracker
// Mirrors content.js (Instagram) section-for-section: same CONFIG shape,
// same buffer/batch/send pipeline, same chrome.runtime.sendMessage relay to
// background.js (page CSP blocks a direct fetch from here). Only the
// target-detection and metadata-extraction sections are YouTube-specific —
// see the plan doc for why (YouTube is an SPA; Instagram's viewport-video
// pattern only gets us the video element, not "which page are we on").

(function () {
  'use strict';

  // ==================== CONFIGURATION ====================

  const CONFIG = {
    CHECK_INTERVAL: 1000,
    MIN_WATCH_TIME: 2, // longer than Instagram's 0.5s — YouTube nav/preview churn is noisier
    BATCH_SIZE: 10,
    BATCH_INTERVAL: 30000,
    // Debug display only — the actual fetch happens in background.js.
    BACKEND_URL: 'http://localhost:8000/ingest',
    USER_ID: 'test_user_001',
  };

  // ==================== STATE ====================

  const state = {
    target: null,          // { surface: 'watch'|'shorts', videoId } | null
    meta: null,             // cached extraction for the current target
    watched: 0,              // accumulated real playback seconds
    lastCurrentTime: 0,
    sessionId: `sess_yt_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`,
    buffer: [],
    lastBatchTime: Date.now(),
  };

  console.log('[AIMirror-YT] Content script loaded — session:', state.sessionId);

  // ==================== UTILITIES ====================

  // Parse "1,234" / "12.3K" / "5M" -> integer; null for non-numeric.
  function parseCount(txt) {
    if (!txt) return null;
    const m = String(txt).replace(/,/g, '').match(/([\d.]+)\s*([KkMm]?)/);
    if (!m) return null;
    let n = parseFloat(m[1]);
    if (isNaN(n)) return null;
    const u = m[2].toUpperCase();
    if (u === 'K') n *= 1e3; else if (u === 'M') n *= 1e6;
    return Math.round(n);
  }

  function extractHashtags(text) {
    const m = (text || '').match(/#[a-zA-Z0-9_]+/g);
    return m || [];
  }

  function dedupeCaseInsensitive(arr) {
    const seen = new Set();
    const out = [];
    for (const x of arr) {
      const k = x.toLowerCase();
      if (!seen.has(k)) { seen.add(k); out.push(x); }
    }
    return out;
  }

  // ==================== TARGET IDENTIFICATION ====================

  // YouTube is an SPA — the URL IS the state machine. Instagram's approach
  // (diff the active <video> element) doesn't work here because the watch
  // page reuses the same <video> element across SPA navigations.
  function currentTarget() {
    const p = window.location.pathname;
    if (p === '/watch') {
      const v = new URLSearchParams(window.location.search).get('v');
      return v ? { surface: 'watch', videoId: v } : null;
    }
    const m = p.match(/^\/shorts\/([A-Za-z0-9_-]{5,})/);
    if (m) return { surface: 'shorts', videoId: m[1] };
    return null; // home feed, subscriptions, channel pages -> not tracked (MVP)
  }

  function sameTarget(a, b) {
    if (!a || !b) return a === b;
    return a.surface === b.surface && a.videoId === b.videoId;
  }

  // Largest-visible <video> by clipped bounding-rect area — same proven
  // pattern as Instagram's getActiveVideo(). Needed even on the watch page
  // (not just Shorts) because YouTube can have a hidden/preloaded <video>
  // for the next Short or a mini-player.
  function getVideoEl() {
    const videos = document.querySelectorAll('video');
    let best = null, maxArea = 0;
    videos.forEach((video) => {
      const r = video.getBoundingClientRect();
      const vH = Math.min(r.bottom, window.innerHeight) - Math.max(r.top, 0);
      const vW = Math.min(r.right, window.innerWidth) - Math.max(r.left, 0);
      const area = Math.max(0, vH) * Math.max(0, vW);
      if (area > maxArea) { maxArea = area; best = video; }
    });
    return best;
  }

  function isAdShowing() {
    return !!document.querySelector('#movie_player.ad-showing, .ad-showing');
  }

  // ==================== METADATA EXTRACTION ====================

  // Tier 1: YouTube embeds a full metadata JSON blob in an inline <script>
  // at hard page load. Content scripts run in an isolated world, so
  // window.ytInitialPlayerResponse is NOT reachable directly — but the
  // script TEXT is shared DOM and can be parsed. IMPORTANT: this JSON is
  // written once and does NOT update on SPA navigation (related-video
  // clicks are XHR, not reloads), so it silently describes the PREVIOUS
  // video after a nav. Callers must verify videoId freshness (see
  // extractMeta) before trusting it — that check is load-bearing.
  function readPlayerResponse() {
    try {
      const scripts = document.getElementsByTagName('script');
      for (const s of scripts) {
        const text = s.textContent;
        if (!text || text.indexOf('var ytInitialPlayerResponse') !== 0) continue;
        const start = text.indexOf('{');
        if (start < 0) continue;
        const marker = text.indexOf(';var ytInitialData');
        const jsonText = marker > start ? text.slice(start, marker) : text.slice(start, text.lastIndexOf(';'));
        return JSON.parse(jsonText);
      }
    } catch (e) {
      console.warn('[AIMirror-YT] Tier-1 parse error (falling back to DOM):', e.message);
    }
    return null;
  }

  function extractMetaTier1(target) {
    const pr = readPlayerResponse();
    const vd = pr && pr.videoDetails;
    if (!vd || vd.videoId !== target.videoId) return null; // absent or stale
    const title = vd.title || '';
    const desc = (vd.shortDescription || '').slice(0, 1500);
    const keywords = Array.isArray(vd.keywords) ? vd.keywords.slice(0, 8) : [];
    const tagsInText = extractHashtags(`${title} ${desc}`);
    const hashtags = dedupeCaseInsensitive([...tagsInText, ...keywords]).slice(0, 8);
    return {
      username: vd.author || 'unknown',
      caption: desc ? `${title}\n${desc}` : title,
      hashtags,
      profileUrl: vd.channelId ? `https://www.youtube.com/channel/${vd.channelId}` : '',
      videoLength: vd.lengthSeconds ? parseFloat(vd.lengthSeconds) : null,
    };
  }

  // Tier 2: DOM selectors. Only used when tier 1 is absent or stale.
  // Selectors are best-effort against YouTube's current DOM (2026) and, like
  // the Instagram extractor before it, will likely need adjustment after
  // live verification — see the extractionFailed drop rule below, which
  // exists specifically so a selector miss degrades to "skip" rather than
  // "record a wrong/empty creator".
  function extractMetaTier2(target) {
    let username = 'unknown', caption = '', profileUrl = '';
    try {
      if (target.surface === 'shorts') {
        const a = document.querySelector(
          'ytd-reel-video-renderer[is-active] a[href^="/@"], #shorts-container a[href^="/@"]'
        );
        if (a) {
          username = (a.textContent || '').trim() || 'unknown';
          profileUrl = 'https://www.youtube.com' + (a.getAttribute('href') || '');
        }
        const titleEl = document.querySelector(
          'ytd-reel-video-renderer[is-active] yt-formatted-string.ytd-reel-player-header-renderer, #shorts-container h2'
        );
        if (titleEl) caption = (titleEl.textContent || '').trim();
      } else {
        const titleEl = document.querySelector('ytd-watch-metadata h1 yt-formatted-string, h1.ytd-watch-metadata');
        if (titleEl) caption = (titleEl.textContent || '').trim();

        const chEl = document.querySelector('#owner #channel-name a, ytd-channel-name a');
        if (chEl) {
          username = (chEl.textContent || '').trim() || 'unknown';
          profileUrl = 'https://www.youtube.com' + (chEl.getAttribute('href') || '');
        }

        const descEl = document.querySelector('#description-inline-expander, #description');
        if (descEl) {
          const desc = (descEl.textContent || '').trim().slice(0, 1500);
          if (desc) caption = caption ? `${caption}\n${desc}` : desc;
        }
      }
    } catch (e) {
      console.warn('[AIMirror-YT] Tier-2 extraction error:', e.message);
    }
    return { username, caption, hashtags: extractHashtags(caption), profileUrl, videoLength: null };
  }

  function extractMeta(target) {
    const tier1 = extractMetaTier1(target);
    if (tier1) return { ...tier1, tier: 1 };
    return { ...extractMetaTier2(target), tier: 2 };
  }

  // Engagement state has no tier-1 (JSON) source — it reflects live user
  // interaction, not page-load metadata — so this is always DOM-based.
  function extractEngagement() {
    let liked = false, following = true, likeCount = null, commentCount = null;
    try {
      const likeBtn = document.querySelector(
        'like-button-view-model button[aria-pressed], #segmented-like-button button[aria-pressed], button[aria-label*="like this video" i]'
      );
      if (likeBtn) {
        liked = likeBtn.getAttribute('aria-pressed') === 'true';
        const label = likeBtn.getAttribute('aria-label') || '';
        const m = label.match(/[\d,.]+\s*[KkMm]?/);
        if (m) likeCount = parseCount(m[0]);
      }
      // A button reading "Subscribe" (not "Subscribed") means we do NOT follow.
      const subBtn = document.querySelector('#subscribe-button button, ytd-subscribe-button-renderer button');
      if (subBtn) {
        const txt = (subBtn.textContent || '').trim().toLowerCase();
        following = txt.includes('subscribed') || (!txt.includes('subscribe'));
      }
      const countEl = document.querySelector('#count .count-text, ytd-comments-header-renderer #count');
      if (countEl) commentCount = parseCount((countEl.textContent || '').trim());
    } catch (e) {
      console.warn('[AIMirror-YT] Engagement extraction error:', e.message);
    }
    return { liked, following, likeCount, commentCount };
  }

  // ==================== WATCH SESSION ====================

  function startWatching(target) {
    state.target = target;
    // Extract at START, not stop (opposite of Instagram): YouTube metadata
    // is fully available immediately, and by the time watching stops an SPA
    // nav may have already swapped the DOM to the next video.
    state.meta = { ...extractMeta(target), ...extractEngagement() };
    state.watched = 0;
    const v = getVideoEl();
    state.lastCurrentTime = v ? v.currentTime : 0;
    console.log('[AIMirror-YT] ▶ Watching:', target.surface, target.videoId, `(tier ${state.meta.tier})`);
  }

  function accumulateWatchTime() {
    const v = getVideoEl();
    if (!v || !state.target) return;
    if (!v.paused && !v.ended && !isAdShowing()) {
      const d = v.currentTime - state.lastCurrentTime;
      // Clamp so a seek/scrub doesn't register as watch time.
      if (d > 0 && d < 2 * (CONFIG.CHECK_INTERVAL / 1000) + 0.5) state.watched += d;
    }
    state.lastCurrentTime = v.currentTime;
  }

  function stopWatching() {
    if (!state.target || !state.meta) {
      state.target = null;
      state.meta = null;
      return;
    }

    const { target, meta, watched } = state;

    if (watched >= CONFIG.MIN_WATCH_TIME) {
      // Same drop rule as Instagram: a totally-failed extraction (no
      // channel, no title) would pollute the twin with an "unknown"
      // creator — skip it, the video is re-captured if watched again.
      const extractionFailed = meta.username === 'unknown' && !meta.caption;
      if (extractionFailed) {
        console.log('[AIMirror-YT] ⤫ Skipped (metadata not ready):', target.videoId, `(${watched.toFixed(1)}s)`);
      } else {
        const event = {
          reel_id: target.videoId,
          username: meta.username,
          caption: meta.caption,
          hashtags: meta.hashtags,
          audio_info: '',
          audio_id: '',
          watch_time: parseFloat(watched.toFixed(2)),
          liked: meta.liked,
          saved: false, // YouTube's Save is a modal with no persistent inline state to read
          following: meta.following,
          profile_url: meta.profileUrl,
          like_count: meta.likeCount,
          comment_count: meta.commentCount,
          repost_count: null, // no YouTube concept
          source_url: window.location.href,
          timestamp: new Date().toISOString(),
          session_id: state.sessionId,
          platform: 'youtube',
          surface: target.surface,
          video_length: meta.videoLength,
        };

        state.buffer.push(event);
        console.log('[AIMirror-YT] ■ Stopped:', target.videoId,
          `(${watched.toFixed(1)}s)`, meta.username, `liked=${meta.liked}`);
      }

      checkBatch();
    }

    state.target = null;
    state.meta = null;
    state.watched = 0;
  }

  function checkTarget() {
    const next = currentTarget();

    if (!next) {
      if (state.target) stopWatching();
      return;
    }

    if (sameTarget(state.target, next)) {
      accumulateWatchTime();
      return;
    }

    if (state.target) stopWatching();
    startWatching(next);
  }

  // ==================== BATCHING ====================
  // Identical to content.js — reuse, don't reinvent.

  function checkBatch() {
    const sizeReached = state.buffer.length >= CONFIG.BATCH_SIZE;
    const timeReached = Date.now() - state.lastBatchTime >= CONFIG.BATCH_INTERVAL;
    if (sizeReached || timeReached) sendBatch();
  }

  function sendBatch() {
    if (state.buffer.length === 0) return;

    const events = [...state.buffer];
    state.buffer = [];
    state.lastBatchTime = Date.now();

    const payload = { user_id: CONFIG.USER_ID, events };

    console.log(`[AIMirror-YT] → Sending ${events.length} events via background worker`);

    try {
      chrome.runtime.sendMessage(
        { type: 'SEND_EVENTS', payload },
        (resp) => {
          if (chrome.runtime.lastError) {
            console.error('[AIMirror-YT] ✗ Send failed:', chrome.runtime.lastError.message);
            state.buffer = [...events, ...state.buffer];
            return;
          }
          if (resp && resp.success) {
            console.log('[AIMirror-YT] ✓ Batch sent:', resp.data?.message || resp.data);
          } else {
            console.error('[AIMirror-YT] ✗ Backend error:', resp && resp.error);
            state.buffer = [...events, ...state.buffer]; // retry next cycle
          }
        }
      );
    } catch (err) {
      console.error('[AIMirror-YT] ✗ sendMessage threw:', err.message);
      state.buffer = [...events, ...state.buffer];
    }
  }

  // ==================== INITIALIZATION ====================

  function initialize() {
    if (!window.location.hostname.includes('youtube.com')) {
      console.log('[AIMirror-YT] Not YouTube — skipping');
      return;
    }

    console.log('[AIMirror-YT] Initializing tracker...');

    setInterval(checkTarget, CONFIG.CHECK_INTERVAL);
    setInterval(checkBatch, CONFIG.BATCH_INTERVAL);

    // Fast-path refresh on SPA navigation — YouTube fires this custom event,
    // but it's undocumented and could disappear, so the 1s poll above
    // remains the source of truth; this just reduces the window between a
    // nav and target-change detection.
    window.addEventListener('yt-navigate-finish', checkTarget);

    try {
      chrome.runtime.sendMessage({ type: 'TRACKER_INITIALIZED', sessionId: state.sessionId });
    } catch (_) { /* background not ready */ }

    console.log('[AIMirror-YT] Tracker ready');
  }

  // ==================== CLEANUP ====================

  window.addEventListener('beforeunload', () => {
    if (state.target) stopWatching();
    if (state.buffer.length > 0) sendBatch();
  });

  // ==================== DEBUG ====================

  // Run `aimirrorYtDebug()` in a YouTube tab's console to see exactly what
  // the extractor currently reads.
  window.aimirrorYtDebug = function () {
    const target = currentTarget();
    const meta = target ? extractMeta(target) : null;
    const engagement = target ? extractEngagement() : null;
    console.table({
      session: state.sessionId,
      target: target ? `${target.surface}:${target.videoId}` : '(none)',
      watched: `${state.watched.toFixed(1)}s`,
      bufferSize: state.buffer.length,
      backend: CONFIG.BACKEND_URL,
    });
    if (meta) console.table(meta);
    if (engagement) console.table(engagement);
    return { state, meta, engagement };
  };

  // ==================== START ====================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }
})();
