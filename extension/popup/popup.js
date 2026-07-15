/**
 * SEO Inspector — Popup Logic
 * Manifest V3 Chrome Extension
 * Freemium: FREE = meta, headings, word count, basic score
 *           PREMIUM = keywords, backlinks, competitor, exports
 */

// ==========================================================================
// Constants
// ==========================================================================

const API_BASE = 'http://hernestagent.duckdns.org';
const CACHE_KEY_PREFIX = 'seo_cache_';
const CACHE_TTL_MS = 60 * 60 * 1000;
const PREMIUM_KEY = 'seo_premium_status';
const TOKEN_KEY = 'seo_auth_token';
const SETTINGS_KEY = 'seo_settings';

// ==========================================================================
// State
// ==========================================================================

let currentTab = null;
let analysisData = null;
let isPremium = false;
let activePanel = 'overview';

// ==========================================================================
// Init
// ==========================================================================

document.addEventListener('DOMContentLoaded', async () => {
  bindEvents();
  await loadPremiumStatus();
  await loadSettings();
  await initAnalysis();
});

// ==========================================================================
// Event Bindings
// ==========================================================================

function bindEvents() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  document.getElementById('settingsBtn').addEventListener('click', toggleSettings);

  document.getElementById('retryBtn').addEventListener('click', initAnalysis);

  document.getElementById('upgradeKeywords').addEventListener('click', openUpgrade);
  document.getElementById('footerUpgrade').addEventListener('click', openUpgrade);

  document.getElementById('authLoginBtn').addEventListener('click', handleAuthLogin);
  document.getElementById('authRegisterLink').addEventListener('click', handleAuthRegister);
  document.getElementById('authCancelBtn').addEventListener('click', hideAuthModal);
}

// ==========================================================================
// Auth
// ==========================================================================

async function getToken() {
  try {
    const result = await chrome.storage.local.get(TOKEN_KEY);
    return result[TOKEN_KEY] || null;
  } catch {
    return null;
  }
}

async function storeToken(tok) {
  await chrome.storage.local.set({ [TOKEN_KEY]: tok });
}

async function clearToken() {
  await chrome.storage.local.remove(TOKEN_KEY);
}

// ==========================================================================
// Premium Status
// ==========================================================================

async function loadPremiumStatus() {
  const token = await getToken();
  if (token) {
    try {
      const res = await fetch(`${API_BASE}/api/payments/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        isPremium = data.premium === true;
        await chrome.storage.local.set({ [PREMIUM_KEY]: isPremium });
      }
    } catch {
      const local = await chrome.storage.local.get(PREMIUM_KEY);
      isPremium = local[PREMIUM_KEY] === true;
    }
  } else {
    const local = await chrome.storage.local.get(PREMIUM_KEY);
    isPremium = local[PREMIUM_KEY] === true;
    if (!isPremium) {
      await chrome.storage.local.set({ [PREMIUM_KEY]: false });
    }
  }
  updatePremiumUI();
}

function updatePremiumUI() {
  const statusEl = document.getElementById('premiumStatus');
  const upgradeBtn = document.getElementById('footerUpgrade');

  if (isPremium) {
    statusEl.innerHTML = '<span class="badge badge-pro">Pro</span>';
    upgradeBtn.classList.add('hidden');
  } else {
    statusEl.innerHTML = '<span class="badge badge-free">Free</span>';
    upgradeBtn.classList.remove('hidden');
  }

  // Show/hide premium banners
  document.querySelectorAll('.premium-banner, .premium-locked').forEach(el => {
    if (isPremium) {
      el.classList.add('hidden');
    } else {
      el.classList.remove('hidden');
    }
  });
}

// ==========================================================================
// Settings
// ==========================================================================

async function loadSettings() {
  try {
    const result = await chrome.storage.local.get(SETTINGS_KEY);
    if (result[SETTINGS_KEY]) {
      // Apply saved settings
    }
  } catch {
    // Defaults
  }
}

function toggleSettings() {
  // Future: show settings panel
}

// ==========================================================================
// Analysis Init
// ==========================================================================

async function initAnalysis() {
  showLoading(true);
  hideError();

  try {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    currentTab = tab;

    // Show URL
    document.getElementById('pageUrl').textContent = truncateUrl(tab.url, 45);

    // Check cache
    const cached = await getCachedResult(tab.url);
    if (cached) {
      analysisData = cached;
      renderResults();
      showLoading(false);
      return;
    }

    // Inject content script and get page HTML
    let html;
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => ({
          html: document.documentElement.outerHTML,
          title: document.title,
          url: window.location.href
        })
      });
      html = results[0].result.html;
    } catch {
      // Content script may already be injected
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'getPageData' });
      html = response.html;
    }

    // Analyze locally (fast, no API dependency for core features)
    analysisData = analyzeLocally(html, tab.url);
    analysisData.pageSizeKB = Math.round(html.length / 1024);

    // Try backend API for richer analysis
    try {
      const apiResult = await callBackendAPI(html, tab.url);
      if (apiResult) {
        analysisData = { ...analysisData, ...apiResult };
      }
    } catch {
      // Backend unavailable, use local analysis
    }

    // Cache results
    await cacheResult(tab.url, analysisData);

    // Render
    renderResults();

  } catch (err) {
    console.error('SEO Inspector error:', err);
    showError('Unable to analyze this page. The page may restrict access.');
  }

  showLoading(false);
}

// ==========================================================================
// Local Analysis Engine
// ==========================================================================

function analyzeLocally(html, url) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');

  // --- Meta Tags ---
  const title = doc.querySelector('title');
  const titleText = title ? title.textContent.trim() : '';

  const metaDesc = doc.querySelector('meta[name="description"]');
  const metaDescText = metaDesc ? metaDesc.getAttribute('content') || '' : '';

  const metaKeywords = doc.querySelector('meta[name="keywords"]');
  const metaKeywordsText = metaKeywords ? metaKeywords.getAttribute('content') || '' : '';

  const metaRobots = doc.querySelector('meta[name="robots"]');
  const metaRobotsText = metaRobots ? metaRobots.getAttribute('content') || '' : '';

  const canonical = doc.querySelector('link[rel="canonical"]');
  const canonicalHref = canonical ? canonical.getAttribute('href') || '' : '';

  const ogTitle = doc.querySelector('meta[property="og:title"]');
  const ogTitleText = ogTitle ? ogTitle.getAttribute('content') || '' : '';

  const ogDesc = doc.querySelector('meta[property="og:description"]');
  const ogDescText = ogDesc ? ogDesc.getAttribute('content') || '' : '';

  const ogImage = doc.querySelector('meta[property="og:image"]');
  const ogImageText = ogImage ? ogImage.getAttribute('content') || '' : '';

  const viewport = doc.querySelector('meta[name="viewport"]');
  const viewportText = viewport ? viewport.getAttribute('content') || '' : '';

  // --- Headings ---
  const headings = {};
  for (let i = 1; i <= 6; i++) {
    const elements = doc.querySelectorAll(`h${i}`);
    headings[`h${i}`] = Array.from(elements).map(el => ({
      text: el.textContent.trim(),
      level: i
    }));
  }

  // --- Links ---
  const allLinks = doc.querySelectorAll('a[href]');
  const links = Array.from(allLinks).map(a => ({
    href: a.getAttribute('href'),
    text: a.textContent.trim(),
    rel: a.getAttribute('rel') || '',
    isExternal: isExternalUrl(a.getAttribute('href'), url),
    isNofollow: (a.getAttribute('rel') || '').includes('nofollow')
  }));

  const internalLinks = links.filter(l => !l.isExternal);
  const externalLinks = links.filter(l => l.isExternal);
  const nofollowLinks = links.filter(l => l.isNofollow);
  const brokenLinkCandidates = links.filter(l =>
    l.href === '#' || l.href === '' || l.href === 'javascript:void(0)'
  );

  // --- Images ---
  const allImages = doc.querySelectorAll('img');
  const images = Array.from(allImages).map(img => ({
    src: img.getAttribute('src') || '',
    alt: img.getAttribute('alt') || '',
    width: img.getAttribute('width') || '',
    height: img.getAttribute('height') || '',
    hasAlt: img.hasAttribute('alt'),
    altEmpty: img.hasAttribute('alt') && img.getAttribute('alt').trim() === '',
    noAlt: !img.hasAttribute('alt')
  }));

  const imagesWithoutAlt = images.filter(i => i.noAlt || i.altEmpty);

  // --- Word Count ---
  const body = doc.querySelector('body');
  const bodyText = body ? body.textContent.replace(/\s+/g, ' ').trim() : '';
  const wordCount = bodyText ? bodyText.split(/\s+/).length : 0;

  // --- Readability ---
  const sentences = bodyText.split(/[.!?]+/).filter(s => s.trim().length > 0);
  const avgSentenceLength = sentences.length > 0
    ? wordCount / sentences.length
    : 0;

  // --- Scoring ---
  const scores = calculateScores({
    title: titleText,
    metaDesc: metaDescText,
    headings,
    images,
    imagesWithoutAlt,
    links,
    internalLinks,
    externalLinks,
    wordCount,
    hasViewport: !!viewportText,
    hasCanonical: !!canonicalHref,
    hasOG: !!(ogTitleText || ogDescText)
  });

  return {
    url,
    title: titleText,
    meta: {
      title: { content: titleText, length: titleText.length, score: scores.metaTitle },
      description: { content: metaDescText, length: metaDescText.length, score: scores.metaDesc },
      keywords: { content: metaKeywordsText, length: metaKeywordsText.length },
      robots: { content: metaRobotsText },
      canonical: { href: canonicalHref },
      ogTitle: { content: ogTitleText },
      ogDescription: { content: ogDescText },
      ogImage: { content: ogImageText },
      viewport: { content: viewportText }
    },
    headings: {
      h1: headings.h1 || [],
      h2: headings.h2 || [],
      h3: headings.h3 || [],
      h4: headings.h4 || [],
      h5: headings.h5 || [],
      h6: headings.h6 || [],
      total: Object.values(headings).flat().length,
      hasH1: (headings.h1 || []).length > 0,
      hasMultipleH1: (headings.h1 || []).length > 1,
      score: scores.headings
    },
    links: {
      total: links.length,
      internal: internalLinks.length,
      external: externalLinks.length,
      nofollow: nofollowLinks.length,
      brokenCandidates: brokenLinkCandidates.length,
      score: scores.links
    },
    images: {
      total: images.length,
      withoutAlt: imagesWithoutAlt.length,
      score: scores.images
    },
    content: {
      wordCount,
      sentenceCount: sentences.length,
      avgSentenceLength: Math.round(avgSentenceLength * 10) / 10
    },
    overall: {
      score: scores.overall,
      grade: getGrade(scores.overall),
      maxScore: 100,
      breakdown: {
        meta: scores.metaScore,
        headings: scores.headings,
        links: scores.links,
        images: scores.images,
        content: scores.content
      }
    }
  };
}

function calculateScores(data) {
  // Meta Title (0-25)
  let metaTitle = 0;
  if (data.title) {
    const len = data.title.length;
    if (len >= 30 && len <= 60) metaTitle = 25;
    else if (len >= 20 && len <= 70) metaTitle = 17;
    else if (len > 0) metaTitle = 8;
  }

  // Meta Description (0-25)
  let metaDesc = 0;
  if (data.metaDesc) {
    const len = data.metaDesc.length;
    if (len >= 120 && len <= 160) metaDesc = 25;
    else if (len >= 80 && len <= 180) metaDesc = 17;
    else if (len > 0) metaDesc = 8;
  }

  const metaScore = metaTitle + metaDesc;

  // Headings (0-25)
  let headings = 0;
  if (data.headings.hasH1 && !data.headings.hasMultipleH1) headings += 15;
  if (data.headings.h2.length > 0) headings += 5;
  if (data.headings.h3.length > 0) headings += 3;
  if (data.headings.h4.length > 0) headings += 2;

  // Links (0-15)
  let links = 15;
  if (data.internalLinks.length === 0) links -= 5;
  if (data.externalLinks.length === 0 && data.links.length > 0) links -= 3;

  // Images (0-10)
  let images = 10;
  if (data.images.total > 0) {
    const altRatio = data.imagesWithoutAlt.length / data.images.total;
    if (altRatio > 0.5) images = 3;
    else if (altRatio > 0.2) images = 6;
  }

  // Content (bonus, factored into overall)
  let content = 0;
  if (data.wordCount >= 300) content = 5;

  const overall = Math.min(100, metaScore + headings + links + images + content);

  return { metaTitle, metaDesc, metaScore, headings, links, images, content, overall };
}

function getGrade(score) {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 70) return 'C';
  if (score >= 60) return 'D';
  return 'F';
}

// ==========================================================================
// API Call (optional, non-blocking)
// ==========================================================================

async function callBackendAPI(html, url) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${API_BASE}/api/seo/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html, url }),
      signal: controller.signal
    });

    clearTimeout(timeout);

    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

// ==========================================================================
// Caching
// ==========================================================================

async function getCachedResult(url) {
  try {
    const key = CACHE_KEY_PREFIX + hashUrl(url);
    const result = await chrome.storage.local.get(key);
    const cached = result[key];
    if (cached && (Date.now() - cached.timestamp) < CACHE_TTL_MS) {
      return cached.data;
    }
  } catch {}
  return null;
}

async function cacheResult(url, data) {
  try {
    const key = CACHE_KEY_PREFIX + hashUrl(url);
    await chrome.storage.local.set({
      [key]: { data, timestamp: Date.now() }
    });
  } catch {}
}

function hashUrl(url) {
  let hash = 0;
  for (let i = 0; i < url.length; i++) {
    const char = url.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return Math.abs(hash).toString(36);
}

// ==========================================================================
// Render
// ==========================================================================

function renderResults() {
  if (!analysisData) return;

  const d = analysisData;

  // Score
  renderScore(d.overall.score);

  // Overview
  document.getElementById('metaScore').textContent = d.meta?.title?.score ?? '--';
  document.getElementById('headingScore').textContent = d.headings?.score ?? '--';
  document.getElementById('linkScore').textContent = d.links?.score ?? '--';
  document.getElementById('imageScore').textContent = d.images?.score ?? '--';

  document.getElementById('sumTitle').textContent =
    d.meta?.title?.content
      ? `${d.meta.title.length} chars — ${d.meta.title.score < 17 ? 'Could be better' : 'Good'}`
      : 'Missing';

  document.getElementById('sumDesc').textContent =
    d.meta?.description?.content
      ? `${d.meta.description.length} chars — ${d.meta.description.score < 17 ? 'Could be better' : 'Good'}`
      : 'Missing';

  document.getElementById('sumWords').textContent =
    `${d.content?.wordCount || 0} words`;

  document.getElementById('sumLoad').textContent =
    `${d.pageSizeKB || '--'} KB`;

  // Summary item classes
  updateSummaryClass('sumTitle', d.meta?.title?.score, 17);
  updateSummaryClass('sumDesc', d.meta?.description?.score, 17);

  // Meta checklist
  renderMetaChecklist(d);

  // Headings
  renderHeadings(d);

  // Links
  renderLinks(d);

  // Images
  renderImages(d);

  // Show results
  document.getElementById('resultsContainer').classList.remove('hidden');
}

function renderScore(score) {
  const circumference = 2 * Math.PI * 52; // r=52
  const offset = circumference - (score / 100) * circumference;
  const arc = document.getElementById('scoreArc');

  arc.style.strokeDasharray = circumference;
  arc.style.strokeDashoffset = offset;

  // Color
  arc.classList.remove('score-good', 'score-ok', 'score-poor');
  if (score >= 80) arc.classList.add('score-good');
  else if (score >= 60) arc.classList.add('score-ok');
  else arc.classList.add('score-poor');

  document.getElementById('scoreNumber').textContent = score;
  document.getElementById('scoreLabel').textContent = getGrade(score) + ' Grade';
}

function updateSummaryClass(elId, score, threshold) {
  const el = document.querySelector(`#${elId}`).parentElement;
  el.classList.remove('good', 'warn', 'bad');
  if (score === undefined) el.classList.add('good');
  else if (score >= threshold) el.classList.add('good');
  else if (score > 0) el.classList.add('warn');
  else el.classList.add('bad');
}

function renderMetaChecklist(d) {
  const items = [
    {
      label: 'Title Tag',
      value: d.meta?.title?.content || 'Missing',
      status: d.meta?.title?.content
        ? (d.meta.title.length >= 30 && d.meta.title.length <= 60 ? 'pass' : 'warn')
        : 'fail',
      advice: d.meta?.title?.content
        ? (d.meta.title.length < 30 ? 'Too short — aim for 30–60 chars'
          : d.meta.title.length > 60 ? 'Too long — trim to 60 chars' : null)
        : 'Add a title tag (30–60 characters)'
    },
    {
      label: 'Meta Description',
      value: d.meta?.description?.content || 'Missing',
      status: d.meta?.description?.content
        ? (d.meta.description.length >= 120 && d.meta.description.length <= 160 ? 'pass' : 'warn')
        : 'fail',
      advice: d.meta?.description?.content
        ? (d.meta.description.length < 120 ? 'Too short — aim for 120–160 chars'
          : d.meta.description.length > 160 ? 'Too long — trim to 160 chars' : null)
        : 'Add a meta description (120–160 characters)'
    },
    {
      label: 'Canonical URL',
      value: d.meta?.canonical?.href || 'Missing',
      status: d.meta?.canonical?.href ? 'pass' : 'warn',
      advice: d.meta?.canonical?.href ? null : 'Consider adding a canonical URL'
    },
    {
      label: 'Viewport Meta',
      value: d.meta?.viewport?.content || 'Missing',
      status: d.meta?.viewport?.content ? 'pass' : 'fail',
      advice: d.meta?.viewport?.content ? null : 'Add a viewport meta tag for mobile'
    },
    {
      label: 'Robots Meta',
      value: d.meta?.robots?.content || 'Not set',
      status: d.meta?.robots?.content && d.meta.robots.content.includes('noindex') ? 'warn' : 'pass',
      advice: d.meta?.robots?.content?.includes('noindex') ? 'Page is set to noindex!' : null
    },
    {
      label: 'Open Graph Title',
      value: d.meta?.ogTitle?.content || 'Missing',
      status: d.meta?.ogTitle?.content ? 'pass' : 'warn',
      advice: d.meta?.ogTitle?.content ? null : 'Add OG tags for social sharing'
    }
  ];

  const container = document.getElementById('metaChecklist');
  container.innerHTML = items.map(item => `
    <div class="checklist-item">
      <div class="check-icon ${item.status}">
        ${item.status === 'pass' ? svgCheck() : item.status === 'warn' ? svgWarn() : svgFail()}
      </div>
      <div class="check-body">
        <div class="check-label">${item.label}</div>
        <div class="check-value">${escapeHtml(item.value)}</div>
        ${item.advice ? `<div class="check-advice">${item.advice}</div>` : ''}
      </div>
    </div>
  `).join('');
}

function renderHeadings(d) {
  const container = document.getElementById('headingHierarchy');
  const allHeadings = [
    ...(d.headings?.h1 || []).map(h => ({ ...h, tag: 'H1' })),
    ...(d.headings?.h2 || []).map(h => ({ ...h, tag: 'H2' })),
    ...(d.headings?.h3 || []).map(h => ({ ...h, tag: 'H3' })),
    ...(d.headings?.h4 || []).map(h => ({ ...h, tag: 'H4' })),
    ...(d.headings?.h5 || []).map(h => ({ ...h, tag: 'H5' })),
    ...(d.headings?.h6 || []).map(h => ({ ...h, tag: 'H6' })),
  ];

  if (allHeadings.length === 0) {
    container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 12px;">No headings found</p>';
    return;
  }

  container.innerHTML = allHeadings.slice(0, 20).map(h => `
    <div class="heading-row">
      <span class="h-tag">${h.tag}</span>
      <span class="h-text" title="${escapeHtml(h.text)}">${escapeHtml(h.text)}</span>
    </div>
  `).join('');

  if (allHeadings.length > 20) {
    container.innerHTML += `<p style="color: var(--text-muted); font-size: 11px; text-align: center; padding: 6px;">
      +${allHeadings.length - 20} more headings
    </p>`;
  }
}

function renderLinks(d) {
  const container = document.getElementById('linksSummary');
  container.innerHTML = `
    <div class="stat-row">
      <span class="stat-label">Total Links</span>
      <span class="stat-value">${d.links?.total || 0}</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">Internal</span>
      <span class="stat-value success">${d.links?.internal || 0}</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">External</span>
      <span class="stat-value">${d.links?.external || 0}</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">Nofollow</span>
      <span class="stat-value">${d.links?.nofollow || 0}</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">Potentially Broken</span>
      <span class="stat-value ${d.links?.brokenCandidates > 0 ? 'danger' : 'success'}">${d.links?.brokenCandidates || 0}</span>
    </div>
  `;
}

function renderImages(d) {
  const container = document.getElementById('imagesSummary');
  const withoutAlt = d.images?.withoutAlt || 0;
  const total = d.images?.total || 0;
  const altPct = total > 0 ? Math.round(((total - withoutAlt) / total) * 100) : 100;

  container.innerHTML = `
    <div class="stat-row">
      <span class="stat-label">Total Images</span>
      <span class="stat-value">${total}</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">With Alt Text</span>
      <span class="stat-value ${altPct >= 80 ? 'success' : altPct >= 50 ? '' : 'danger'}">${total - withoutAlt} (${altPct}%)</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">Missing Alt</span>
      <span class="stat-value ${withoutAlt > 0 ? 'danger' : 'success'}">${withoutAlt}</span>
    </div>
  `;
}

// ==========================================================================
// Tab Switching
// ==========================================================================

function switchTab(tabName) {
  activePanel = tabName;

  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabName);
  });

  document.querySelectorAll('.tab-panel').forEach(p => {
    p.classList.toggle('active', p.id === `panel-${tabName}`);
  });
}

// ==========================================================================
// Loading / Error States
// ==========================================================================

function showLoading(show) {
  document.getElementById('loadingSpinner').classList.toggle('hidden', !show);
  if (show) {
    document.getElementById('resultsContainer').classList.add('hidden');
    document.getElementById('scoreNumber').textContent = '--';
  }
}

function showError(message) {
  document.getElementById('errorMessage').textContent = message;
  document.getElementById('errorState').classList.remove('hidden');
}

function hideError() {
  document.getElementById('errorState').classList.add('hidden');
}

// ==========================================================================
// Upgrade
// ==========================================================================

async function openUpgrade() {
  const token = await getToken();
  if (token) {
    startStripeCheckout(token);
    return;
  }
  showAuthModal('login');
}

async function startStripeCheckout(token) {
  try {
    const res = await fetch(`${API_BASE}/api/payments/create-checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        success_url: `${API_BASE}/upgrade?success=1`,
        cancel_url: `${API_BASE}/upgrade?cancel=1`
      })
    });
    const data = await res.json();
    if (res.ok && data.url) {
      chrome.tabs.create({ url: data.url });
    } else {
      chrome.tabs.create({ url: `${API_BASE}/upgrade` });
    }
  } catch {
    chrome.tabs.create({ url: `${API_BASE}/upgrade` });
  }
}

function showAuthModal(mode) {
  document.getElementById('authOverlay').classList.remove('hidden');
  document.getElementById('authError').classList.add('hidden');
  document.getElementById('authEmail').value = '';
  document.getElementById('authPassword').value = '';
  if (mode === 'register') {
    document.getElementById('authLoginBtn').textContent = 'Register';
    document.getElementById('authRegisterLink').parentElement.classList.add('hidden');
  } else {
    document.getElementById('authLoginBtn').textContent = 'Log In';
    document.getElementById('authRegisterLink').parentElement.classList.remove('hidden');
  }
  document.getElementById('authLoginBtn').dataset.mode = mode;
  document.getElementById('authEmail').focus();
}

function hideAuthModal() {
  document.getElementById('authOverlay').classList.add('hidden');
}

async function handleAuthLogin() {
  const mode = document.getElementById('authLoginBtn').dataset.mode;
  const email = document.getElementById('authEmail').value.trim();
  const password = document.getElementById('authPassword').value;

  if (!email || !password) {
    showAuthError('Email and password are required');
    return;
  }
  if (password.length < 8) {
    showAuthError('Password must be at least 8 characters');
    return;
  }

  const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Authentication failed');

    await storeToken(data.access_token);
    hideAuthModal();
    await loadPremiumStatus();
    startStripeCheckout(data.access_token);
  } catch (err) {
    showAuthError(err.message);
  }
}

async function handleAuthRegister(e) {
  e.preventDefault();
  showAuthModal('register');
}

function showAuthError(msg) {
  const el = document.getElementById('authError');
  el.textContent = msg;
  el.classList.remove('hidden');
}

// ==========================================================================
// Helpers
// ==========================================================================

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function truncateUrl(url, max) {
  if (!url) return '';
  if (url.length <= max) return url;
  return url.substring(0, max - 3) + '...';
}

function isExternalUrl(href, pageUrl) {
  if (!href) return false;
  if (href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('tel:')) return false;
  try {
    const linkHost = new URL(href, pageUrl).hostname;
    const pageHost = new URL(pageUrl).hostname;
    return linkHost !== pageHost;
  } catch {
    return false;
  }
}

// ==========================================================================
// SVG Icons
// ==========================================================================

function svgCheck() {
  return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
}

function svgWarn() {
  return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
}

function svgFail() {
  return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
}
