/**
 * SEO Inspector — Content Script
 * Injected into every page to extract HTML and metadata.
 * Manifest V3
 */

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'getPageData') {
    sendResponse({
      html: document.documentElement.outerHTML,
      title: document.title,
      url: window.location.href,
      metaTags: extractMetaTags(),
      timestamp: Date.now()
    });
    return true; // Keep channel open for async
  }

  if (message.action === 'ping') {
    sendResponse({ status: 'ok' });
    return true;
  }
});

/**
 * Extract all meta tags from the page.
 */
function extractMetaTags() {
  const tags = {};
  document.querySelectorAll('meta').forEach(meta => {
    const name = meta.getAttribute('name') ||
                 meta.getAttribute('property') ||
                 meta.getAttribute('http-equiv') ||
                 meta.getAttribute('charset');
    const content = meta.getAttribute('content') || meta.getAttribute('charset') || '';
    if (name) {
      tags[name] = content;
    }
  });
  return tags;
}
