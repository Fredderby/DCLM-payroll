document.addEventListener("DOMContentLoaded", function () {
  const navLinks = Array.from(document.querySelectorAll(".sidebar-menu a"));
  if (!navLinks.length) return;

  const currentPath = location.pathname.replace(/\/$/, "") || "/";

  navLinks.forEach((link) => {
    const linkPath =
      new URL(link.href, location.origin).pathname.replace(/\/$/, "") || "/";
    if (linkPath === currentPath) {
      link.classList.add("active");
      link.setAttribute("aria-current", "page");
    }

    link.addEventListener("click", () => {
      navLinks.forEach((item) => item.classList.remove("active"));
      link.classList.add("active");
    });
  });
});
