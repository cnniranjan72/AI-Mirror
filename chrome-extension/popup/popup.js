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

  // Load initial stats
  loadStats();

  // Event listeners
  syncBtn.addEventListener('click', handleSync);
  dashboardBtn.addEventListener('click', handleDashboard);
  clearBtn.addEventListener('click', handleClear);

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
    chrome.tabs.create({ url: 'http://localhost:5173' });
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
