// AIMirror Popup Script

document.addEventListener('DOMContentLoaded', () => {
  console.log('[AIMirror Popup] Loaded');

  // Elements
  const sessionCountEl = document.getElementById('sessionCount');
  const eventCountEl = document.getElementById('eventCount');
  const statusIndicator = document.getElementById('statusIndicator');
  const statusText = document.getElementById('statusText');
  const syncBtn = document.getElementById('syncBtn');
  const dashboardBtn = document.getElementById('dashboardBtn');
  const clearBtn = document.getElementById('clearBtn');

  // Backend elements
  const backendEventCountEl = document.getElementById('backendEventCount');
  const personaLabelEl = document.getElementById('personaLabel');
  const personaLabelSub = document.getElementById('personaLabelSub');
  const backendIndicator = document.getElementById('backendIndicator');
  const backendStatusText = document.getElementById('backendStatusText');

  // Extraction-warning elements
  const extractionWarningBanner = document.getElementById('extractionWarningBanner');
  const extractionWarningText = document.getElementById('extractionWarningText');

  // Load initial stats
  loadStats();
  loadBackendStatus();
  loadExtractionWarnings();

  // Event listeners
  syncBtn.addEventListener('click', handleSync);
  dashboardBtn.addEventListener('click', handleDashboard);
  clearBtn.addEventListener('click', handleClear);
  document.getElementById('settingsLink').addEventListener('click', (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });

  // ==================== FUNCTIONS ====================

  async function loadStats() {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'GET_SESSION_INFO' });
      
      if (response.success) {
        sessionCountEl.textContent = response.totalSessions;
        eventCountEl.textContent = response.totalEvents;

        if (response.activeSessions > 0) {
          statusIndicator.className = 'status-indicator active';
          statusText.textContent = 'Tracking active';
        } else {
          statusIndicator.className = 'status-indicator inactive';
          statusText.textContent = 'No active tracking';
        }
      }
    } catch (error) {
      console.error('[AIMirror Popup] Failed to load stats:', error);
      statusIndicator.className = 'status-indicator inactive';
      statusText.textContent = 'Error loading stats';
    }
  }

  async function loadBackendStatus() {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'GET_BACKEND_STATUS' });

      if (response.connected) {
        backendIndicator.className = 'status-indicator-backend connected';
        backendStatusText.textContent = 'Connected';

        backendEventCountEl.textContent = response.backendEvents || 0;

        if (response.persona) {
          personaLabelEl.textContent = response.persona.label;
          const pct = Math.round((response.persona.confidence || 0) * 100);
          personaLabelSub.textContent = `Persona · ${pct}% confidence`;
        } else if (response.identityConfidence) {
          personaLabelEl.textContent = 'Identity';
          const pct = Math.round(response.identityConfidence * 100);
          personaLabelSub.textContent = `v${response.identityVersion || '?'} · ${pct}%`;
        } else {
          personaLabelEl.textContent = '--';
          personaLabelSub.textContent = 'No data yet';
        }
      } else {
        backendIndicator.className = 'status-indicator-backend disconnected';
        backendStatusText.textContent = 'Offline';
        backendEventCountEl.textContent = '?';
        personaLabelEl.textContent = '--';
        personaLabelSub.textContent = 'Offline';
      }
    } catch (_) {
      backendIndicator.className = 'status-indicator-backend disconnected';
      backendStatusText.textContent = 'Error';
    }
  }

  // Surfaces content-script extraction failures (e.g. YouTube/Instagram
  // changing their DOM so a selector stops matching) that were previously
  // only a console.log — invisible unless you had devtools open at the
  // exact moment it happened. This is the counter background.js increments
  // each time a batch includes dropped-item warnings.
  async function loadExtractionWarnings() {
    try {
      const { extractionFailureCount = 0 } = await chrome.storage.local.get(['extractionFailureCount']);
      if (extractionFailureCount > 0) {
        extractionWarningText.textContent =
          `${extractionFailureCount} item${extractionFailureCount === 1 ? '' : 's'} couldn't be read this session — the page structure may have changed.`;
        extractionWarningBanner.style.display = 'flex';
      } else {
        extractionWarningBanner.style.display = 'none';
      }
    } catch (error) {
      console.error('[AIMirror Popup] Failed to load extraction warnings:', error);
    }
  }

  async function handleSync() {
    syncBtn.disabled = true;
    syncBtn.innerHTML = '<span class="btn-icon">⏳</span> Syncing...';

    try {
      const response = await chrome.runtime.sendMessage({ type: 'SYNC_NOW' });
      
      if (response.success) {
        syncBtn.innerHTML = '<span class="btn-icon">✅</span> Synced!';
        setTimeout(() => {
          syncBtn.innerHTML = '<span class="btn-icon">🔄</span> Sync Now';
          syncBtn.disabled = false;
          loadStats();
          loadBackendStatus();
        }, 2000);
      } else {
        syncBtn.innerHTML = '<span class="btn-icon">❌</span> Sync Failed';
        setTimeout(() => {
          syncBtn.innerHTML = '<span class="btn-icon">🔄</span> Sync Now';
          syncBtn.disabled = false;
        }, 2000);
      }
    } catch (error) {
      console.error('[AIMirror Popup] Sync failed:', error);
      syncBtn.innerHTML = '<span class="btn-icon">❌</span> Error';
      setTimeout(() => {
        syncBtn.innerHTML = '<span class="btn-icon">🔄</span> Sync Now';
        syncBtn.disabled = false;
      }, 2000);
    }
  }

  function handleDashboard() {
    chrome.storage.local.get(['dashboardUrl'], (result) => {
      chrome.tabs.create({ url: result.dashboardUrl || 'http://localhost:5173' });
    });
  }

  async function handleClear() {
    const confirmed = confirm('Are you sure you want to clear all local data? This cannot be undone.');
    
    if (confirmed) {
      clearBtn.disabled = true;
      clearBtn.innerHTML = '<span class="btn-icon">⏳</span> Clearing...';

      try {
        const response = await chrome.runtime.sendMessage({ type: 'CLEAR_DATA' });
        
        if (response.success) {
          clearBtn.innerHTML = '<span class="btn-icon">✅</span> Cleared!';
          setTimeout(() => {
            clearBtn.innerHTML = '<span class="btn-icon">🗑️</span> Clear Data';
            clearBtn.disabled = false;
            loadStats();
            loadExtractionWarnings();
          }, 2000);
        }
      } catch (error) {
        console.error('[AIMirror Popup] Clear failed:', error);
        clearBtn.innerHTML = '<span class="btn-icon">❌</span> Error';
        setTimeout(() => {
          clearBtn.innerHTML = '<span class="btn-icon">🗑️</span> Clear Data';
          clearBtn.disabled = false;
        }, 2000);
      }
    }
  }
});
