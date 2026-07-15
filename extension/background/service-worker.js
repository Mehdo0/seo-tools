/**
 * SEO Inspector — Background Service Worker
 * Manifest V3
 * Handles: API calls, caching coordination, premium checks, Stripe redirects
 */

// ==========================================================================
// Constants
// ==========================================================================

const API_BASE = 'http://hernestagent.duckdns.org';
const STRIPE_UPGRADE_URL = 'http://hernestagent.duckdns.org/upgrade';
const PREMIUM_CHECK_URL = 'http://hernestagent.duckdns.org/api/user/premium-status';
const CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour

// ==========================================================================
// Install & Update
// ==========================================================================

chrome.runtime.onInstalled.addListener((details) => {
  console.log('SEO Inspector installed:', details.reason);

  // Set default settings
  if (details.reason === 'install') {
    chrome.storage.local.set({
      seo_settings: {
        autoAnalyze: true,
        showNotifications: false,
        cacheEnabled: true
      }
    });
  }
});

// ==========================================================================
// Message Handling
// ==========================================================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.action) {
    case 'analyze':
      handleAnalyze(message.data, sender, sendResponse);
      return true; // Keep channel open

    case 'checkPremium':
      handlePremiumCheck(sendResponse);
      return true;

    case 'openUpgrade':
      handleUpgrade();
      sendResponse({ success: true });
      return false;

    case 'getCachedAnalysis':
      handleGetCached(message.url, sendResponse);
      return true;

    case 'clearCache':
      handleClearCache(sendResponse);
      return true;

    default:
      sendResponse({ error: 'Unknown action' });
      return false;
  }
});

// ==========================================================================
// Analysis Handler
// ==========================================================================

async function handleAnalyze(data, sender, sendResponse) {
  try {
    const { html, url } = data;

    // Check cache first
    const cachedKey = `seo_analysis_${hashString(url)}`;
    const cached = await chrome.storage.local.get(cachedKey);

    if (cached[cachedKey] && (Date.now() - cached[cachedKey].timestamp) < CACHE_TTL_MS) {
      sendResponse({ success: true, data: cached[cachedKey].data, cached: true });
      return;
    }

    // Call backend API
    let apiResult = null;
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);

      const response = await fetch(`${API_BASE}/api/seo/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ html, url }),
        signal: controller.signal
      });

      clearTimeout(timeout);

      if (response.ok) {
        apiResult = await response.json();
      }
    } catch (err) {
      console.warn('Backend API unavailable, using local analysis:', err.message);
    }

    // Cache the result
    if (apiResult) {
      await chrome.storage.local.set({
        [cachedKey]: { data: apiResult, timestamp: Date.now() }
      });
    }

    sendResponse({ success: true, data: apiResult, cached: false });
  } catch (err) {
    console.error('Analysis error:', err);
    sendResponse({ success: false, error: err.message });
  }
}

// ==========================================================================
// Premium Check
// ==========================================================================

async function handlePremiumCheck(sendResponse) {
  try {
    // Check local first
    const stored = await chrome.storage.local.get('seo_premium_status');
    if (stored.seo_premium_status !== undefined) {
      sendResponse({ premium: stored.seo_premium_status === true, source: 'local' });
      return;
    }

    // Check with backend
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(PREMIUM_CHECK_URL, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal
    });

    clearTimeout(timeout);

    if (response.ok) {
      const data = await response.json();
      const isPremium = data.premium === true;
      await chrome.storage.local.set({ seo_premium_status: isPremium });
      sendResponse({ premium: isPremium, source: 'api' });
    } else {
      sendResponse({ premium: false, source: 'fallback' });
    }
  } catch {
    sendResponse({ premium: false, source: 'error' });
  }
}

// ==========================================================================
// Upgrade Handler
// ==========================================================================

async function handleUpgrade() {
  chrome.tabs.create({ url: STRIPE_UPGRADE_URL });
}

// ==========================================================================
// Cache Handlers
// ==========================================================================

async function handleGetCached(url, sendResponse) {
  try {
    const key = `seo_analysis_${hashString(url)}`;
    const cached = await chrome.storage.local.get(key);

    if (cached[key] && (Date.now() - cached[key].timestamp) < CACHE_TTL_MS) {
      sendResponse({ success: true, data: cached[key].data });
    } else {
      sendResponse({ success: false, error: 'No valid cache' });
    }
  } catch (err) {
    sendResponse({ success: false, error: err.message });
  }
}

async function handleClearCache(sendResponse) {
  try {
    const all = await chrome.storage.local.get(null);
    const keysToRemove = Object.keys(all).filter(k => k.startsWith('seo_analysis_'));
    if (keysToRemove.length > 0) {
      await chrome.storage.local.remove(keysToRemove);
    }
    sendResponse({ success: true, removed: keysToRemove.length });
  } catch (err) {
    sendResponse({ success: false, error: err.message });
  }
}

// ==========================================================================
// Action click — open popup with active tab analysis
// ==========================================================================

chrome.action.onClicked.addListener((tab) => {
  // Popup opens automatically via default_popup in manifest
  // This is a fallback for programmatic opening
});

// ==========================================================================
// Periodic premium re-check (every 24 hours)
// ==========================================================================

chrome.alarms.create('premiumCheck', { periodInMinutes: 1440 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'premiumCheck') {
    handlePremiumCheck((response) => {
      console.log('Premium status check:', response);
    });
  }
});

// ==========================================================================
// Helpers
// ==========================================================================

function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return Math.abs(hash).toString(36);
}
