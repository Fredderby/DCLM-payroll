/**
 * DCLM Payroll - Client-Side Navigation System
 * Enables smooth page transitions without full reloads.
 * Uses history.pushState for URL management and fetch for partial content loading.
 * 
 * IMPORTANT: This script self-guards against double initialization.
 */
(function () {
  'use strict';

  // Guard: only run once
  if (window.__SPA_NAV_INITIALIZED) return;
  window.__SPA_NAV_INITIALIZED = true;

  // ── State ──
  var isLoading = false;
  var pendingRequest = null;

  // ── DOM Cache ──
  var mainContent = null;
  var contentWrapper = null;
  var skeletonEl = null;

  // ── Init ──
  function init() {
    mainContent = document.querySelector('.main-content');
    if (!mainContent) return;

    // Create content wrapper inside main-content (if not already present)
    contentWrapper = document.getElementById('content-wrapper');
    if (!contentWrapper) {
      contentWrapper = document.createElement('div');
      contentWrapper.id = 'content-wrapper';
      contentWrapper.style.cssText = 'transition: opacity 0.2s ease; min-height: 60vh;';
      
      // Move existing children into the wrapper
      while (mainContent.firstChild) {
        if (mainContent.firstChild.id === 'page-skeleton') {
          mainContent.removeChild(mainContent.firstChild);
          continue;
        }
        contentWrapper.appendChild(mainContent.firstChild);
      }
      mainContent.appendChild(contentWrapper);
    }

    // Create skeleton loader (hidden by default)
    skeletonEl = document.getElementById('page-skeleton');
    if (!skeletonEl) {
      skeletonEl = document.createElement('div');
      skeletonEl.id = 'page-skeleton';
      skeletonEl.style.cssText = 'display:none; padding: 20px 0;';
      mainContent.appendChild(skeletonEl);
    }

    // Intercept all navigation clicks
    interceptNavClicks();
    
    // Handle browser back/forward
    window.addEventListener('popstate', function (e) {
      if (e.state && e.state.url) {
        navigateTo(e.state.url, { replace: true, fromPopState: true });
      }
    });

    // Update current URL in state
    updateNavState();
  }

  // ── Skeleton Loader HTML ──
  function getSkeletonHTML() {
    return '' +
      '<div class="skeleton skeleton-text" style="width:250px;height:28px;margin-bottom:24px;"></div>' +
      '<div class="stats-row" style="margin-bottom:24px;">' +
        '<div class="stat-card"><div class="skeleton skeleton-text" style="width:40px;height:32px;"></div><div class="skeleton skeleton-text short" style="margin-top:8px;"></div></div>' +
        '<div class="stat-card"><div class="skeleton skeleton-text" style="width:40px;height:32px;"></div><div class="skeleton skeleton-text short" style="margin-top:8px;"></div></div>' +
        '<div class="stat-card"><div class="skeleton skeleton-text" style="width:40px;height:32px;"></div><div class="skeleton skeleton-text short" style="margin-top:8px;"></div></div>' +
        '<div class="stat-card"><div class="skeleton skeleton-text" style="width:40px;height:32px;"></div><div class="skeleton skeleton-text short" style="margin-top:8px;"></div></div>' +
      '</div>' +
      '<div class="card-modern">' +
        '<div class="card-modern-header"><div class="skeleton skeleton-text short"></div></div>' +
        '<div class="card-modern-body">' +
          '<div class="skeleton skeleton-text"></div>' +
          '<div class="skeleton skeleton-text"></div>' +
          '<div class="skeleton skeleton-text short"></div>' +
        '</div>' +
      '</div>';
  }

  // ── Get targeted skeleton for specific route ──
  function getRouteSkeleton(path) {
    if (path.indexOf('/staff') !== -1 && path.indexOf('/edit') === -1 && path.indexOf('/delete') === -1) {
      return '' +
        '<div class="top-bar"><div><div class="skeleton skeleton-text" style="width:180px;height:28px;"></div></div></div>' +
        '<div class="card-modern">' +
          '<div class="card-modern-header"><div class="skeleton skeleton-text short"></div></div>' +
          '<div class="card-modern-body">' +
            '<div class="skeleton skeleton-text" style="height:300px;"></div>' +
          '</div>' +
        '</div>';
    }
    if (path.indexOf('/payslips') !== -1) {
      return '' +
        '<div class="top-bar"><div><div class="skeleton skeleton-text" style="width:180px;height:28px;"></div></div></div>' +
        '<div class="card-modern">' +
          '<div class="card-modern-header"><div class="skeleton skeleton-text short"></div></div>' +
          '<div class="card-modern-body">' +
            '<div class="skeleton skeleton-text" style="height:200px;"></div>' +
          '</div>' +
        '</div>';
    }
    return getSkeletonHTML();
  }

  // ── Intercept Navigation Clicks ──
  function interceptNavClicks() {
    document.addEventListener('click', function (e) {
      // Find closest anchor tag
      var link = e.target.closest('a');
      if (!link) return;
      
      var href = link.getAttribute('href');
      if (!href) return;
      
      // Skip external links, downloads, anchors, logout
      if (href.indexOf('http') === 0 && href.indexOf(window.location.origin) !== 0) return;
      if (href.indexOf('#') === 0 || href.indexOf('mailto:') === 0 || href.indexOf('tel:') === 0) return;
      if (href.indexOf('/logout') !== -1) return; // Allow logout as full navigation
      if (link.hasAttribute('download') || link.target === '_blank') return;
      
      // Skip download links (they need full page navigation for file delivery)
      if (href.indexOf('/download') !== -1) return;
      
      // Skip POST forms/buttons
      if (link.closest('form') && link.type === 'submit') return;
      if (link.getAttribute('data-no-spa')) return;
      
      e.preventDefault();
      e.stopPropagation();
      
      var url = href.indexOf('/') === 0 ? href : new URL(href, window.location.origin).pathname;
      navigateTo(url);
    });
  }

  // ── Navigate to a page ──
  function navigateTo(url, options) {
    options = options || {};
    
    // Normalize URL
    var fullUrl = url.indexOf('/') === 0 ? url : new URL(url, window.location.origin).pathname;
    
    // Don't navigate to same page
    if (!options.force && window.location.pathname === fullUrl) return;
    
    // Cancel any pending request
    if (pendingRequest) {
      pendingRequest.abort();
      pendingRequest = null;
    }
    
    isLoading = true;
    
    if (!options.replace) {
      window.history.pushState({ url: fullUrl }, '', fullUrl);
    }
    
    // Show skeleton
    showSkeleton(fullUrl);
    
    // Create abort controller
    var controller = new AbortController();
    pendingRequest = controller;
    
    // Fetch the page content
    fetch(fullUrl, {
      signal: controller.signal,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'text/html, application/json'
      }
    })
    .then(function (response) {
      pendingRequest = null;
      
      if (!response.ok) {
        if (response.status === 401 || response.status === 307 || response.status === 303) {
          window.location.href = '/login';
          return;
        }
        throw new Error('Page load failed: ' + response.status);
      }
      return response.text();
    })
    .then(function (html) {
      if (!html) return;
      isLoading = false;
      hideSkeleton();
      
      // Extract content from the response HTML
      var content = extractContent(html);
      if (content) {
        contentWrapper.innerHTML = content;
      } else {
        window.location.href = fullUrl;
        return;
      }
      
      // Re-run inline scripts in the content
      reExecuteScripts(contentWrapper);
      
      // Update active nav state
      updateNavState();
      
      // Scroll to top smoothly
      window.scrollTo({ top: 0, behavior: 'smooth' });
      
      // Update page title from response
      updateTitle(html);
      
      // Re-run content-loaded initialization
      document.dispatchEvent(new Event('content-loaded'));
    })
    .catch(function (err) {
      pendingRequest = null;
      if (err.name === 'AbortError') return;
      isLoading = false;
      hideSkeleton();
      console.error('Navigation error:', err);
      window.location.href = fullUrl;
    });
  }

  // ── Extract content from full HTML page ──
  function extractContent(html) {
    var parser = new DOMParser();
    var doc = parser.parseFromString(html, 'text/html');
    
    var contentEl = doc.querySelector('.main-content');
    if (!contentEl) return null;
    
    // Remove the navigation element if present
    var navMount = contentEl.querySelector('#navigation-mount');
    if (navMount) navMount.remove();
    
    return contentEl.innerHTML;
  }

  // ── Update page title ──
  function updateTitle(html) {
    var match = html.match(/<title>([^<]*)<\/title>/);
    if (match && match[1]) {
      document.title = match[1];
    }
  }

  // ── Re-execute inline scripts in new content ──
  function reExecuteScripts(container) {
    var scripts = container.querySelectorAll('script');
    for (var i = 0; i < scripts.length; i++) {
      var oldScript = scripts[i];
      var newScript = document.createElement('script');
      
      // Copy attributes (except src for now)
      for (var j = 0; j < oldScript.attributes.length; j++) {
        var attr = oldScript.attributes[j];
        newScript.setAttribute(attr.name, attr.value);
      }
      
      if (oldScript.src) {
        newScript.src = oldScript.src;
      } else {
        newScript.textContent = oldScript.textContent;
      }
      
      oldScript.parentNode.replaceChild(newScript, oldScript);
    }
  }

  // ── Show/Hide Skeleton ──
  function showSkeleton(url) {
    skeletonEl.innerHTML = getRouteSkeleton(url);
    contentWrapper.style.opacity = '0';
    contentWrapper.style.pointerEvents = 'none';
    skeletonEl.style.display = 'block';
  }

  function hideSkeleton() {
    contentWrapper.style.opacity = '1';
    contentWrapper.style.pointerEvents = '';
    skeletonEl.style.display = 'none';
  }

  // ── Update Active Nav State ──
  function updateNavState() {
    var curPath = window.location.pathname.replace(/\/+$/, '').toLowerCase();
    
    // Dispatch custom event for React sidebar
    window.dispatchEvent(new CustomEvent('nav-changed', { detail: { path: curPath } }));
    
    // Also update via CSS class for fallback
    var links = document.querySelectorAll('.sidebar-menu a, #ns-nav a');
    for (var i = 0; i < links.length; i++) {
      var link = links[i];
      var linkPath = (link.getAttribute('href') || '').replace(/\/+$/, '').toLowerCase();
      if (linkPath === curPath) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      } else {
        link.classList.remove('active');
        link.removeAttribute('aria-current');
      }
    }
  }

  // ── Start when DOM is ready ──
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }

})();
