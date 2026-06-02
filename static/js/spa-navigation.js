/**
 * DCLM Payroll - SPA Navigation System v6
 * 
 * KEY FIXES:
 * 1. Force full page reload on login redirect (`_fresh=true`)
 * 2. Re-executes ALL scripts from loaded content (fixes post-login button activation)
 * 3. Properly re-binds inline event handlers (onclick, onsubmit, etc.)
 * 4. Reinitializes page-specific JavaScript after content swap
 * 5. Loads extra scripts from head that aren't already loaded
 * 6. Fires events for other modules to reinitialize
 * 7. Handles forms with inline onsubmit properly
 */

(function() {
  'use strict';

  // Guard against double init
  if (window.__spaNavInitialized) return;
  window.__spaNavInitialized = true;

    // Force full page reload if coming from login (fresh=true param)
  // CRITICAL: After login, the auth cookie is set but SPA navigation would cache
  // the previous page state, causing all buttons/actions to be non-functional.
  // A full reload ensures all JS initializes fresh with the authenticated context.
  if (window.location.href.indexOf("_fresh=true") !== -1) {
    var cleanUrl = window.location.href.replace(/[?&]_fresh=true/g, "").replace(/&&/g, "&").replace(/\?&/g, "?").replace(/\/\?/g, "/?");
    if (cleanUrl !== window.location.href && cleanUrl.length > 0) {
      window.history.replaceState({}, "", cleanUrl);
    }
    // Full page reload to ensure all modules reinitialize with auth context
    window.location.reload(true);
    return;
  }  var contentWrapper = document.querySelector('.content-wrapper');
  if (!contentWrapper) return;

  var cache = {};
  var isLoading = false;

  // Global hook system for SPA reinitialization
  window.__spaHooks = window.__spaHooks || [];
  window.addSpaHook = function(fn) { window.__spaHooks.push(fn); };
  window.runSpaHooks = function() {
    var hooks = window.__spaHooks.slice();
    hooks.forEach(function(fn) {
      try { fn(); } catch(e) { console.warn('SPA hook error:', e); }
    });
    // Re-bind menu-tabs active state
    if (window.updateActiveNavTab) {
      try { window.updateActiveNavTab(); } catch(e) {}
    }
  };

  // Expose navigateTo globally
  window.navigateTo = function(url, options) {
    options = options || {};
    if (isLoading) return;

    // Force full reload on _fresh=true (login redirect)
    if (url.indexOf('_fresh=true') !== -1) {
      window.location.href = url;
      return;
    }

    if (url === window.location.pathname && !options.force) return;

    isLoading = true;
    showLoading(true);

    var fullUrl = url;

    // Use cache if available
    if (cache[fullUrl] && !options.force) {
      applyContent(cache[fullUrl], fullUrl);
      window.history.pushState({ url: fullUrl }, '', fullUrl);
      isLoading = false;
      showLoading(false);
      updateActiveNav(fullUrl);
      runSpaHooks();
      return;
    }

    fetch(fullUrl, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(function(res) {
      if (!res.ok) {
        window.location.href = fullUrl;
        throw new Error('Fetch failed');
      }
      return res.text();
    })
    .then(function(html) {
      cache[fullUrl] = html;
      if (options.replace) {
        window.history.replaceState({ url: fullUrl }, '', fullUrl);
      } else {
        window.history.pushState({ url: fullUrl }, '', fullUrl);
      }
      applyContent(html, fullUrl);
      updateActiveNav(fullUrl);
      isLoading = false;
      showLoading(false);
    })
    .catch(function() {
      isLoading = false;
      showLoading(false);
    });
  };

  /**
   * Apply fetched HTML content to the page
   * CRITICAL: Must re-bind ALL scripts and event handlers
   */
  function applyContent(html, url) {
    var temp = document.createElement('div');
    temp.innerHTML = html;

    // Find the content-wrapper in fetched page
    var newContent = temp.querySelector('.content-wrapper');
    if (!newContent) {
      newContent = temp.querySelector('.main-content');
    }
    if (!newContent) {
      newContent = temp.querySelector('body');
    }
    if (!newContent) return;

    // Capture extra inline styles/scripts from throughout the fetched page
    var extraCssBlocks = [];
    var extraScriptsToLoad = [];

    var allExtraStyles = temp.querySelectorAll('style');
    allExtraStyles.forEach(function(s) {
      if (!newContent.contains(s)) {
        extraCssBlocks.push(s.textContent);
      }
    });

    var allExtraScripts = temp.querySelectorAll('script');
    allExtraScripts.forEach(function(s) {
      if (!newContent.contains(s)) {
        if (s.src) {
          extraScriptsToLoad.push(s.src);
        } else {
          extraCssBlocks.push(s.textContent);
        }
      }
    });

    // Replace current content
    contentWrapper.innerHTML = newContent.innerHTML;

    // ═══════════════════════════════════════════════
    // CRITICAL: Re-execute ALL inline scripts
    // ═══════════════════════════════════════════════
    var allScripts = contentWrapper.querySelectorAll('script');
    allScripts.forEach(function(oldScript) {
      var newScript = document.createElement('script');
      if (oldScript.src) {
        newScript.src = oldScript.src;
        newScript.async = false;
      }
      if (oldScript.textContent) {
        newScript.textContent = oldScript.textContent;
      }
      newScript.async = false;
      oldScript.parentNode.replaceChild(newScript, oldScript);
    });

    // ═══════════════════════════════════════════════
    // CRITICAL: Re-bind inline event handlers
    // ═══════════════════════════════════════════════
    var forms = contentWrapper.querySelectorAll('form[onsubmit]');
    forms.forEach(function(form) {
      var handlerCode = form.getAttribute('onsubmit');
      if (handlerCode) {
        form.removeAttribute('onsubmit');
        form.addEventListener('submit', function(e) {
          try { return eval(handlerCode); } catch(err) { return true; }
        });
      }
    });

    var clickElements = contentWrapper.querySelectorAll('[onclick]');
    clickElements.forEach(function(el) {
      var handlerCode = el.getAttribute('onclick');
      if (handlerCode) {
        el.removeAttribute('onclick');
        el.addEventListener('click', function(e) {
          try { return eval(handlerCode); } catch(err) {}
        });
      }
    });

    var changeElements = contentWrapper.querySelectorAll('[onchange]');
    changeElements.forEach(function(el) {
      var handlerCode = el.getAttribute('onchange');
      if (handlerCode) {
        el.removeAttribute('onchange');
        el.addEventListener('change', function(e) {
          try { return eval(handlerCode); } catch(err) {}
        });
      }
    });

    // Inject extra styles
    extraCssBlocks.forEach(function(css) {
      var styleTag = document.createElement('style');
      styleTag.textContent = css;
      document.head.appendChild(styleTag);
    });

    // Load extra scripts (deduped)
    extraScriptsToLoad.forEach(function(src) {
      if (!document.querySelector('script[src="' + src + '"]')) {
        var ns = document.createElement('script');
        ns.src = src;
        ns.async = false;
        document.body.appendChild(ns);
      }
    });

    // ─── Update page header ───
    var headerEl = document.querySelector('.top-header');
    if (headerEl) {
      var newHeader = temp.querySelector('.top-header');
      if (newHeader) {
        var titleEl = headerEl.querySelector('.page-title');
        var newTitleEl = newHeader.querySelector('.page-title');
        if (titleEl && newTitleEl) titleEl.textContent = newTitleEl.textContent;

        var actionsEl = headerEl.querySelector('.top-header-right');
        var newActionsEl = newHeader.querySelector('.top-header-right');
        if (actionsEl && newActionsEl) {
          actionsEl.innerHTML = newActionsEl.innerHTML;
          actionsEl.querySelectorAll('script').forEach(function(s) {
            var ns = document.createElement('script');
            if (s.src) ns.src = s.src;
            else ns.textContent = s.textContent;
            ns.async = false;
            s.parentNode.replaceChild(ns, s);
          });
          var actionClickEls = actionsEl.querySelectorAll('[onclick]');
          actionClickEls.forEach(function(el) {
            var handlerCode = el.getAttribute('onclick');
            if (handlerCode) {
              el.removeAttribute('onclick');
              el.addEventListener('click', function(e) { try { return eval(handlerCode); } catch(err) {} });
            }
          });
        }
      }
    }

    // Dispatch custom events for page-specific initializers
    document.dispatchEvent(new CustomEvent('spa-content-loaded', { detail: { url: url } }));
    document.dispatchEvent(new CustomEvent('content-loaded', { detail: { url: url } }));

    // Run all registered SPA hooks
    setTimeout(runSpaHooks, 10);

    window.scrollTo(0, 0);
  }

  function updateActiveNav(url) {
    var path = url.replace(window.location.origin, '').split('?')[0];
    document.querySelectorAll('[data-nav-link]').forEach(function(link) {
      var href = link.getAttribute('href');
      link.classList.toggle('active', href === path);
    });
    if (window.updateActiveNavTab) window.updateActiveNavTab();
  }

  function showLoading(visible) {
    var bar = document.getElementById('nprogress-bar');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'nprogress-bar';
      bar.style.cssText = 'position:fixed;top:0;left:0;right:0;height:3px;background:#2563eb;z-index:9999;transition:width 0.3s ease,opacity 0.3s ease;';
      document.body.appendChild(bar);
    }
    if (visible) {
      bar.style.width = '60%';
      bar.style.opacity = '1';
    } else {
      bar.style.width = '100%';
      setTimeout(function() { bar.style.opacity = '0'; setTimeout(function() { bar.style.width = '0'; }, 300); }, 200);
    }
  }

  // Single click handler for navigation
  document.addEventListener('click', function(e) {
    var link = e.target.closest('a[href]');
    if (!link || e.defaultPrevented) return;
    var href = link.getAttribute('href');
    if (!href) return;

    // Skip special links
    if (href.startsWith('http') && !href.startsWith(window.location.origin)) return;
    if (href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('tel:')) return;
    if (link.hasAttribute('download') || link.target === '_blank') return;

    // Always do full navigation to login/logout
    if (href === '/logout' || href.startsWith('/login')) return;

    // Skip form actions
    if (link.closest('form')) return;
    if (link.getAttribute('role') === 'button') return;

    // Skip if href is an API endpoint or action endpoint
    if (href.includes('/delete') || href.includes('/generate') || href.includes('/send') || href.includes('/upload') || href.includes('/test')) return;

    e.preventDefault();
    navigateTo(href);
  });

  // Handle back/forward navigation
  window.addEventListener('popstate', function(e) {
    if (e.state && e.state.url) {
      navigateTo(e.state.url, { replace: true });
    }
  });

  // Expose functions globally
  window.spaNavigate = navigateTo;

  // Run initialization on first load
  function onReady() {
    if (window.updateActiveNavTab) {
      window.updateActiveNavTab();
      window.addSpaHook(window.updateActiveNavTab);
    }
    setTimeout(runSpaHooks, 50);
  }

  if (document.readyState === 'complete') {
    setTimeout(onReady, 50);
  } else {
    document.addEventListener('DOMContentLoaded', onReady);
  }
})();
