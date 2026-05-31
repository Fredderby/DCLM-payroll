/**
 * DCLM Payroll - SPA Navigation System v4
 * Smooth page transitions via fetch + history.pushState
 * Leaves sidebar intact - swaps only content area
 */

(function() {
  'use strict';

  // Guard against double init
  if (window.__spaNavInitialized) return;
  window.__spaNavInitialized = true;

  var contentWrapper = document.querySelector('.content-wrapper');
  if (!contentWrapper) return;

  var cache = {};
  var isLoading = false;

  // Expose navigateTo globally
  window.navigateTo = function(url, options) {
    options = options || {};
    if (isLoading) return;
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
      return;
    }

    fetch(fullUrl, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(function(res) {
      if (!res.ok) {
        // Fallback: full page reload
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

  function applyContent(html, url) {
    // Extract the content from fetched page
    var temp = document.createElement('div');
    temp.innerHTML = html;

    // Find the content-wrapper in fetched page
    var newContent = temp.querySelector('.content-wrapper');
    if (!newContent) {
      // Fallback: try to find main-content
      newContent = temp.querySelector('.main-content');
    }
    if (!newContent) {
      // Last fallback: use body content
      newContent = temp.querySelector('body');
    }
    if (!newContent) return;

    // Remove navigation mount point if present (legacy)
    var navMount = newContent.querySelector('#navigation-mount');
    if (navMount) navMount.remove();

    // Replace current content
    contentWrapper.innerHTML = newContent.innerHTML;

    // Re-execute any scripts
    reExecuteScripts(contentWrapper);

    // Dispatch custom event for page-specific initializers
    var event = new CustomEvent('spa-content-loaded', { detail: { url: url } });
    document.dispatchEvent(event);

    // Scroll to top
    window.scrollTo(0, 0);
  }

  function reExecuteScripts(container) {
    var scripts = container.querySelectorAll('script');
    scripts.forEach(function(oldScript) {
      var newScript = document.createElement('script');
      if (oldScript.src) {
        newScript.src = oldScript.src;
      } else {
        newScript.textContent = oldScript.textContent;
      }
      newScript.async = false;
      oldScript.parentNode.replaceChild(newScript, oldScript);
    });
  }

  function updateActiveNav(url) {
    var path = url.replace(window.location.origin, '').split('?')[0];
    var navLinks = document.querySelectorAll('[data-nav-link]');
    navLinks.forEach(function(link) {
      var href = link.getAttribute('href');
      if (href === path) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Update document title
    var navItem = document.querySelector('[data-nav-link].active');
    if (navItem) {
      var label = navItem.querySelector('.nav-label');
      if (label) {
        document.title = label.textContent.trim() + ' - DCLM Payroll';
      }
    }
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
      setTimeout(function() {
        bar.style.opacity = '0';
        setTimeout(function() {
          bar.style.width = '0';
        }, 300);
      }, 200);
    }
  }

  // Intercept link clicks
  document.addEventListener('click', function(e) {
    var link = e.target.closest('a[data-nav-link]');
    if (!link) {
      // Also handle regular links to app pages
      link = e.target.closest('a[href]');
      if (!link) return;
      var href = link.getAttribute('href');
      if (!href) return;
      // Skip external, anchors, download, logout, login
      if (href.startsWith('http') && !href.startsWith(window.location.origin)) return;
      if (href.startsWith('#') || href.startsWith('javascript:') || href === '/logout' || href.startsWith('/login')) return;
      if (link.hasAttribute('download') || link.target === '_blank') return;
      if (href.startsWith('mailto:') || href.startsWith('tel:')) return;
    }

    e.preventDefault();
    var url = link.getAttribute('href');
    if (url) {
      window.navigateTo(url, { replace: url === window.location.pathname });
    }
  });

  // Handle browser back/forward
  window.addEventListener('popstate', function(e) {
    if (e.state && e.state.url) {
      window.navigateTo(e.state.url, { replace: true });
    }
  });

  // Mark initial page
  updateActiveNav(window.location.pathname);

})();
