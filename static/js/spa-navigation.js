/**
 * DCLM Payroll - SPA Navigation System v7
 * 
 * KEY FIXES:
 * 1. Fixed missing newline causing contentWrapper to not be defined on normal loads
 * 2. Force full page reload on login redirect to ensure auth context
 * 3. Re-executes all inline scripts from loaded content
 * 4. Re-binds inline event handlers (onclick, onsubmit, onchange)
 * 5. Registers and runs SPA hooks for page-specific initialization
 * 6. Updates navigation active state after page transitions
 * 7. Shows loading indicator during SPA navigation
 */

(function() {
  'use strict';

  if (window.__spaNavInitialized) return;
  window.__spaNavInitialized = true;

  // Force full page reload when coming from login redirect
  if (window.location.href.indexOf("_fresh=true") !== -1) {
    var cleanUrl = window.location.href.replace(/[?&]_fresh=true/g, "").replace(/&&/g, "&").replace(/\?&/g, "?").replace(/\/\?/g, "/?");
    if (cleanUrl !== window.location.href && cleanUrl.length > 0) {
      window.history.replaceState({}, "", cleanUrl);
    }
    window.location.reload(true);
    return;
  }

  // Core SPA initialization
  var contentWrapper = document.querySelector('.content-wrapper');
  if (!contentWrapper) {
    contentWrapper = document.querySelector('#main-content');
    if (!contentWrapper) return;
  }

  var cache = {};
  var isLoading = false;

  window.__spaHooks = window.__spaHooks || [];
  window.addSpaHook = function(fn) { window.__spaHooks.push(fn); };
  window.runSpaHooks = function() {
    var hooks = window.__spaHooks.slice();
    hooks.forEach(function(fn) {
      try { fn(); } catch(e) { console.warn('SPA hook error:', e); }
    });
    if (window.updateActiveNavTab) {
      try { window.updateActiveNavTab(); } catch(e) {}
    }
  };

  window.navigateTo = function(url, options) {
    options = options || {};
    if (isLoading) return;
    if (url.indexOf('_fresh=true') !== -1) {
      window.location.href = url;
      return;
    }
    if (url === window.location.pathname && !options.force) return;
    isLoading = true;
    showLoading(true);
    var fullUrl = url;
    if (cache[fullUrl] && !options.force) {
      applyContent(cache[fullUrl], fullUrl);
      window.history.pushState({ url: fullUrl }, '', fullUrl);
      isLoading = false;
      showLoading(false);
      updateActiveNav(fullUrl);
      runSpaHooks();
      return;
    }
    fetch(fullUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(function(res) {
      if (!res.ok) { window.location.href = fullUrl; throw new Error('Fetch failed'); }
      return res.text();
    })
    .then(function(html) {
      cache[fullUrl] = html;
      if (options.replace) window.history.replaceState({ url: fullUrl }, '', fullUrl);
      else window.history.pushState({ url: fullUrl }, '', fullUrl);
      applyContent(html, fullUrl);
      updateActiveNav(fullUrl);
      isLoading = false;
      showLoading(false);
    })
    .catch(function() { isLoading = false; showLoading(false); });
  };

  function applyContent(html, url) {
    var temp = document.createElement('div');
    temp.innerHTML = html;
    var newContent = temp.querySelector('.content-wrapper') || temp.querySelector('.main-content') || temp.querySelector('body');
    if (!newContent) return;
    
    // Extract scripts and styles from the new content BEFORE innerHTML replacement
    var scriptsToExecute = [];
    newContent.querySelectorAll('script').forEach(function(s) {
      scriptsToExecute.push({ src: s.src, text: s.textContent });
    });
    
    contentWrapper.innerHTML = newContent.innerHTML;
    
    // Re-execute all inline scripts from the new content
    scriptsToExecute.forEach(function(s) {
      var ns = document.createElement('script');
      if (s.src) ns.src = s.src;
      if (s.text) ns.textContent = s.text;
      ns.async = false;
      document.body.appendChild(ns);
    });
    
    // Re-bind inline event handlers
    contentWrapper.querySelectorAll('form[onsubmit]').forEach(function(f) {
      var c = f.getAttribute('onsubmit'); if (c) { f.removeAttribute('onsubmit'); f.addEventListener('submit', function(e) { try { return eval(c); } catch(err) { return true; } }); }
    });
    contentWrapper.querySelectorAll('[onclick]').forEach(function(el) {
      var c = el.getAttribute('onclick'); if (c) { el.removeAttribute('onclick'); el.addEventListener('click', function(e) { try { return eval(c); } catch(err) {} }); }
    });
    contentWrapper.querySelectorAll('[onchange]').forEach(function(el) {
      var c = el.getAttribute('onchange'); if (c) { el.removeAttribute('onchange'); el.addEventListener('change', function(e) { try { return eval(c); } catch(err) {} }); }
    });
    
    // Handle head-level styles and scripts
    var extraCss = [], extraScripts = [];
    temp.querySelectorAll('style').forEach(function(s) { if (!newContent.contains(s)) extraCss.push(s.textContent); });
    temp.querySelectorAll('script').forEach(function(s) { if (!newContent.contains(s)) { if (s.src) extraScripts.push(s.src); } });
    extraCss.forEach(function(css) { var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st); });
    extraScripts.forEach(function(src) { if (!document.querySelector('script[src="' + src + '"]')) { var ns = document.createElement('script'); ns.src = src; ns.async = false; document.body.appendChild(ns); } });
    
    // Update header
    var header = document.querySelector('.top-header');
    if (header) {
      var nh = temp.querySelector('.top-header');
      if (nh) {
        var h1 = header.querySelector('.page-title'), nh1 = nh.querySelector('.page-title');
        if (h1 && nh1) h1.textContent = nh1.textContent;
        var ac = header.querySelector('.top-header-right'), nac = nh.querySelector('.top-header-right');
        if (ac && nac) { ac.innerHTML = nac.innerHTML; }
      }
    }
    document.dispatchEvent(new CustomEvent('spa-content-loaded', { detail: { url: url } }));
    document.dispatchEvent(new CustomEvent('content-loaded', { detail: { url: url } }));
    setTimeout(runSpaHooks, 10);
    window.scrollTo(0, 0);
  }

  function updateActiveNav(url) {
    var path = url.replace(window.location.origin, '').split('?')[0];
    document.querySelectorAll('[data-nav-link]').forEach(function(link) { link.classList.toggle('active', link.getAttribute('href') === path); });
    if (window.updateActiveNavTab) window.updateActiveNavTab();
  }

  function showLoading(v) {
    var bar = document.getElementById('nprogress-bar');
    if (!bar) { bar = document.createElement('div'); bar.id = 'nprogress-bar'; bar.style.cssText = 'position:fixed;top:0;left:0;right:0;height:3px;background:#2563eb;z-index:9999;transition:width 0.3s ease,opacity 0.3s ease;'; document.body.appendChild(bar); }
    if (v) { bar.style.width = '60%'; bar.style.opacity = '1'; }
    else { bar.style.width = '100%'; setTimeout(function() { bar.style.opacity = '0'; setTimeout(function() { bar.style.width = '0'; }, 300); }, 200); }
  }

  document.addEventListener('click', function(e) {
    var link = e.target.closest('a[href]');
    if (!link || e.defaultPrevented) return;
    var href = link.getAttribute('href');
    if (!href) return;
    if (href.startsWith('http') && !href.startsWith(window.location.origin)) return;
    if (href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('tel:')) return;
    if (link.hasAttribute('download') || link.target === '_blank') return;
    if (href === '/logout' || href.startsWith('/login')) return;
    if (link.closest('form')) return;
    if (link.getAttribute('role') === 'button') return;
    if (href.includes('/delete') || href.includes('/generate') || href.includes('/send') || href.includes('/upload') || href.includes('/test') || href.includes('/download')) return;
    e.preventDefault();
    navigateTo(href);
  });

  window.addEventListener('popstate', function(e) { if (e.state && e.state.url) navigateTo(e.state.url, { replace: true }); });
  window.spaNavigate = navigateTo;

  function onReady() {
    if (window.updateActiveNavTab) { window.updateActiveNavTab(); window.addSpaHook(window.updateActiveNavTab); }
    setTimeout(runSpaHooks, 50);
  }
  if (document.readyState === 'complete') setTimeout(onReady, 50);
  else document.addEventListener('DOMContentLoaded', onReady);
})();
