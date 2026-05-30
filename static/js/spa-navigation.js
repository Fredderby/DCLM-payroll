/**
 * DCLM Payroll - Client-Side Navigation System v2
 * Enables smooth page transitions without full reloads.
 * Uses history.pushState + fetch for partial content loading.
 * 
 * Fixes: payslips tab blink, location.reload intercept, layout mismatch
 * 
 * IMPORTANT: Self-guards against double initialization.
 */
(function () {
  'use strict';

  if (window.__SPA_NAV_INITIALIZED) return;
  window.__SPA_NAV_INITIALIZED = true;

  var isLoading = false;
  var pendingRequest = null;
  // Simple LRU page cache: stores HTML for previously visited pages
  var pageCache = {};
  var CACHE_MAX = 5;

  var mainContent = null;
  var contentWrapper = null;
  var skeletonEl = null;

  // Intercept location.reload() to do SPA re-fetch instead of full reload
  var origReload = window.location.__proto__ && window.location.__proto__.reload
    ? window.location.__proto__.reload.bind(window.location)
    : function(){ window.location.reload(true); };

  function spaReload() {
    var cur = window.location.pathname;
    // Clear cache for current page so we get fresh data
    delete pageCache[cur];
    navigateTo(cur, { force: true, replace: true });
  }

  // Replace location.reload globally
  try {
    Object.defineProperty(window.location, 'reload', {
      value: function(){
        // If SPA is initialized, do smooth re-fetch
        if (window.__SPA_NAV_INITIALIZED) {
          spaReload();
        } else {
          origReload();
        }
      },
      writable: false
    });
  } catch(e) {
    // If defineProperty fails (some browsers), keep original behavior
  }

  // Also patch the window.location.reload directly
  window.location.reload = function(){
    if (window.__SPA_NAV_INITIALIZED) {
      spaReload();
    } else {
      origReload();
    }
  };

  function init() {
    mainContent = document.querySelector('.main-content');
    if (!mainContent) return;

    contentWrapper = document.getElementById('content-wrapper');
    if (!contentWrapper) {
      contentWrapper = document.createElement('div');
      contentWrapper.id = 'content-wrapper';
      contentWrapper.style.cssText = 'transition: opacity 0.18s ease; min-height: 60vh;';
      
      while (mainContent.firstChild) {
        if (mainContent.firstChild.id === 'page-skeleton') {
          mainContent.removeChild(mainContent.firstChild);
          continue;
        }
        contentWrapper.appendChild(mainContent.firstChild);
      }
      mainContent.appendChild(contentWrapper);
    }

    skeletonEl = document.getElementById('page-skeleton');
    if (!skeletonEl) {
      skeletonEl = document.createElement('div');
      skeletonEl.id = 'page-skeleton';
      skeletonEl.style.cssText = 'display:none; padding: 20px 0;';
      mainContent.appendChild(skeletonEl);
    }

    // Register custom click handler for all navigation links
    setupCustomNavigationHandlers();
    
    window.addEventListener('popstate', function (e) {
      if (e.state && e.state.url) {
        navigateTo(e.state.url, { replace: true, fromPopState: true });
      }
    });

    updateNavState();
  }

  // Setup custom SPA navigation handlers
  function setupCustomNavigationHandlers() {
    // Listen for our custom spa-navigate events
    document.addEventListener('spa-navigate', function(e) {
      if (e.detail && e.detail.path) {
        navigateTo(e.detail.path, { replace: false });
      }
    });

    // Intercept standard anchor clicks as backup mechanism
    document.addEventListener('click', function (e) {
      var link = e.target.closest('a');
      if (!link) return;
      
      var href = link.getAttribute('href');
      if (!href) return;
      
      // Skip navigation interception for specific cases
      if (href.indexOf('http') === 0 && href.indexOf(window.location.origin) !== 0) return;
      if (href.indexOf('#') === 0 || href.indexOf('mailto:') === 0 || href.indexOf('tel:') === 0) return;
      if (href.indexOf('/logout') !== -1) return;
      if (link.hasAttribute('download') || link.target === '_blank') return;
      if (href.indexOf('/download') !== -1) return;
      if (link.closest('form') && link.type === 'submit') return;
      if (link.getAttribute('data-no-spa')) return;
      
      // Check if it's a local internal link
      if (href.startsWith('/') || (href.indexOf(window.location.origin) === 0 && href.indexOf(window.location.origin) !== -1)) {
        e.preventDefault();  // Prevent default browser navigation
        
        var url = href.indexOf('/') === 0 ? href : new URL(href, window.location.origin).pathname;
        navigateTo(url, { replace: false });
      }
    }, true); // Use capture phase to intercept early

    // Handle form submissions appropriately
    document.addEventListener('submit', function (e) {
      var form = e.target;
      if (!form) return;
      
      // Only intercept GET forms (search/filter forms) 
      if (form.method && form.method.toLowerCase() === 'get') {
        e.preventDefault();
        var url = form.action || window.location.pathname;
        navigateTo(url + '?' + new URLSearchParams(new FormData(form)).toString(), { replace: false });
      }
      // POST forms are NOT intercepted - they need to submit normally
    });
  }

  // ── Skeleton Loaders ──
  function getSkeletonHTML() {
    return '' +
      '<div style="padding:20px 0">' +
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
      '</div></div>';
  }

  function getRouteSkeleton(path) {
    // Payslips-specific skeleton that matches the grid layout
    if (path.indexOf('/payslips') !== -1 && path.indexOf('/send') === -1 && path.indexOf('/data') === -1) {
      return '' +
        '<div style="padding:20px 0">' +
        '<div class="skeleton skeleton-text" style="width:180px;height:28px;margin-bottom:8px;"></div>' +
        '<div class="skeleton skeleton-text short" style="width:260px;height:16px;margin-bottom:24px;"></div>' +
        '<div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">' +
          '<div class="rounded-2xl p-5 bg-white/80 border border-white/20" style="height:90px"><div class="skeleton skeleton-text" style="width:60px;height:28px;"></div><div class="skeleton skeleton-text short" style="margin-top:6px;width:80px;"></div></div>' +
          '<div class="rounded-2xl p-5 bg-white/80 border border-white/20" style="height:90px"><div class="skeleton skeleton-text" style="width:60px;height:28px;"></div><div class="skeleton skeleton-text short" style="margin-top:6px;width:80px;"></div></div>' +
          '<div class="rounded-2xl p-5 bg-white/80 border border-white/20" style="height:90px"><div class="skeleton skeleton-text" style="width:60px;height:28px;"></div><div class="skeleton skeleton-text short" style="margin-top:6px;width:80px;"></div></div>' +
          '<div class="rounded-2xl p-5 bg-white/80 border border-white/20" style="height:90px"><div class="skeleton skeleton-text" style="width:60px;height:28px;"></div><div class="skeleton skeleton-text short" style="margin-top:6px;width:80px;"></div></div>' +
        '</div>' +
        '<div class="rounded-2xl bg-white/80 border border-white/20 shadow-lg mb-6" style="height:60px"><div class="skeleton skeleton-text" style="width:300px;height:20px;margin:18px 24px;"></div></div>' +
        '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">' +
          '<div class="rounded-xl bg-white border border-gray-200/60 shadow-sm overflow-hidden" style="height:320px"><div class="skeleton skeleton-text" style="width:100%;height:52px;"></div><div class="p-5"><div class="skeleton skeleton-text" style="margin-bottom:8px;"></div><div class="skeleton skeleton-text" style="margin-bottom:8px;"></div><div class="skeleton skeleton-text" style="margin-bottom:8px;"></div><div class="skeleton skeleton-text" style="margin-bottom:8px;width:80%;"></div></div></div>' +
          '<div class="rounded-xl bg-white border border-gray-200/60 shadow-sm overflow-hidden" style="height:320px"><div class="skeleton skeleton-text" style="width:100%;height:52px;"></div><div class="p-5"><div class="skeleton skeleton-text" style="margin-bottom:8px;"></div><div class="skeleton skeleton-text" style="margin-bottom:8px;"></div><div class="skeleton skeleton-text" style="margin-bottom:8px;"></div><div class="skeleton skeleton-text" style="margin-bottom:8px;width:80%;"></div></div></div>' +
          '<div class="rounded-xl bg-white border border-gray-200/60 shadow-sm overflow-hidden" style="height:320px"><div class="skeleton skeleton-text" style="width:100%;height:52px;"></div><div class="p-5"><div class="skeleton skeleton-text" style="margin-bottom:8px;"></div><div class="skeleton skeleton-text" style="margin-bottom:8px;"></div><div class="skeleton skeleton-text" style="margin-bottom:8px;"></div><div class="skeleton skeleton-text" style="margin-bottom:8px;width:80%;"></div></div></div>' +
        '</div></div>';
    }
    if (path.indexOf('/staff') !== -1 && path.indexOf('/edit') === -1 && path.indexOf('/delete') === -1) {
      return '' +
        '<div style="padding:20px 0">' +
        '<div class="skeleton skeleton-text" style="width:180px;height:28px;margin-bottom:24px;"></div>' +
        '<div class="card-modern">' +
          '<div class="card-modern-header"><div class="skeleton skeleton-text short"></div></div>' +
          '<div class="card-modern-body">' +
            '<div class="skeleton skeleton-text" style="height:300px;"></div>' +
          '</div>' +
        '</div></div>';
    }
    return getSkeletonHTML();
  }

  // ── Navigate to a page (with caching) ──
  function navigateTo(url, options) {
    options = options || {};
    
    var fullUrl = url.indexOf('/') === 0 ? url : new URL(url, window.location.origin).pathname;
    
    if (!options.force && window.location.pathname === fullUrl) return;
    
    if (pendingRequest) {
      pendingRequest.abort();
      pendingRequest = null;
    }
    
    isLoading = true;
    
    // Push state only when not replacing (to properly handle browser back button)
    if (!options.replace) {
      window.history.pushState({ url: fullUrl }, '', fullUrl);
    }
    
    // Check cache first
    if (pageCache[fullUrl] && !options.force) {
      isLoading = false;
      applyContent(pageCache[fullUrl], fullUrl);
      updateNavState();
      return;
    }
    
    showSkeleton(fullUrl);
    
    var controller = new AbortController();
    pendingRequest = controller;
    
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
      
      // Cache the result (limit cache size)
      var keys = Object.keys(pageCache);
      if (keys.length >= CACHE_MAX) {
        delete pageCache[keys[0]];
      }
      pageCache[fullUrl] = html;
      
      isLoading = false;
      hideSkeleton();
      applyContent(html, fullUrl);
      updateNavState();
    })
    .catch(function (err) {
      pendingRequest = null;
      if (err.name === 'AbortError') return;
      isLoading = false;
      hideSkeleton();
      console.error('Navigation error:', err);
      // If we cannot fetch via SPA, fall back to full page navigation
      window.location.href = fullUrl;
    });
  }

  // ── Apply fetched content to the DOM ──
  function applyContent(html, url) {
    var content = extractContent(html);
    if (content) {
      // Prevent blinking effect by using innerHTML instead of replaceChild 
      // and ensure smooth animations
      contentWrapper.style.transition = 'opacity 0.1s ease';
      contentWrapper.style.opacity = '0';
      
      // Defer setting content to allow opacity transition to happen
      setTimeout(() => {
        contentWrapper.innerHTML = content;
        contentWrapper.style.opacity = '1';
        reExecuteScripts(contentWrapper);
        window.scrollTo({ top: 0, behavior: 'smooth' });
        updateTitle(html);
        document.dispatchEvent(new Event('content-loaded'));
      }, 50); // Small delay to ensure opacity transition happens
      
    } else {
      // Fallback if content extraction fails
      window.location.href = url;
      return;
    }
  }

  // ── Extract content from full HTML page ──
  function extractContent(html) {
    var parser = new DOMParser();
    var doc = parser.parseFromString(html, 'text/html');
    
    var contentEl = doc.querySelector('.main-content');
    if (!contentEl) return null;
    
    var navMount = contentEl.querySelector('#navigation-mount');
    if (navMount) navMount.remove();
    
    return contentEl.innerHTML;
  }

  function updateTitle(html) {
    var match = html.match(/<title>([^<]*)<\/title>/);
    if (match && match[1]) {
      document.title = match[1];
    }
  }

  function reExecuteScripts(container) {
    var scripts = container.querySelectorAll('script');
    for (var i = 0; i < scripts.length; i++) {
      var oldScript = scripts[i];
      var newScript = document.createElement('script');
      
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

  function updateNavState() {
    var curPath = window.location.pathname.replace(/\/+$/, '').toLowerCase();
    window.dispatchEvent(new CustomEvent('nav-changed', { detail: { path: curPath } }));
    
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

  // ── Start ──
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }

})();
