const DEFAULT_BACKEND_URL = 'https://aimirror-backend-cu00.onrender.com';
const DEFAULT_DASHBOARD_URL = 'https://aimirror-dashboard.onrender.com';

const backendInput = document.getElementById('backendUrl');
const dashboardInput = document.getElementById('dashboardUrl');
const status = document.getElementById('status');

chrome.storage.local.get(['backendUrl', 'dashboardUrl'], (result) => {
  backendInput.value = result.backendUrl || DEFAULT_BACKEND_URL;
  dashboardInput.value = result.dashboardUrl || DEFAULT_DASHBOARD_URL;
});

document.getElementById('saveBtn').addEventListener('click', () => {
  let backendUrl = backendInput.value.trim().replace(/\/+$/, '') || DEFAULT_BACKEND_URL;
  let dashboardUrl = dashboardInput.value.trim().replace(/\/+$/, '') || DEFAULT_DASHBOARD_URL;
  chrome.storage.local.set({ backendUrl, dashboardUrl }, () => {
    status.textContent = 'Saved. Existing tabs may need a refresh to pick it up.';
    setTimeout(() => { status.textContent = '' }, 4000);
  });
});
