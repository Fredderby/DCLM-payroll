/**
 * Menu Tabs - Active navigation state management
 * Works with SPA navigation system
 */
(function () {
  'use strict';

  function updateActiveNavTab() {
    const navLinks = Array.from(document.querySelectorAll(".sidebar-menu a, #ns-nav a"));
    if (!navLinks.length) return;

    const currentPath = location.pathname.replace(/\/$/, "") || "/";

    navLinks.forEach(function (link) {
      const href = link.getAttribute("href");
      if (!href) return;
      const linkPath = href.replace(/\/$/, "") || "/";
      
      if (linkPath === currentPath) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      } else {
        link.classList.remove("active");
        link.removeAttribute("aria-current");
      }
    });
  }

  // Export function globally
  window.updateActiveNavTab = updateActiveNavTab;

  // Run on initial load
  if (document.readyState === "complete" || document.readyState === "interactive") {
    updateActiveNavTab();
  } else {
    document.addEventListener("DOMContentLoaded", updateActiveNavTab);
  }

  // Listen for SPA content updates
  document.addEventListener("content-loaded", updateActiveNavTab);
})();
