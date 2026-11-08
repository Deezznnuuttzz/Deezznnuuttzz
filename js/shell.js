(() => {
  const views = Array.from(document.querySelectorAll(".view"));
  const topbarContext = document.getElementById("topbar-context");
  const menuToggle = document.getElementById("menu-toggle");
  const mobileNav = document.getElementById("mobile-nav");
  const backdrop = document.getElementById("backdrop");

  function navItems() {
    return Array.from(document.querySelectorAll(".nav-item[data-view]"));
  }

  function setActiveView(name) {
    const next = document.getElementById(`view-${name}`);
    if (!next) return;

    views.forEach((view) => {
      const active = view === next;
      view.classList.toggle("is-active", active);
      view.hidden = !active;
    });

    navItems().forEach((item) => {
      const active = item.dataset.view === name;
      item.classList.toggle("is-active", active);
      if (active) item.setAttribute("aria-current", "page");
      else item.removeAttribute("aria-current");
    });

    if (topbarContext) {
      topbarContext.textContent = next.dataset.title || name;
    }

    closeMobileNav();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function openMobileNav() {
    if (!mobileNav || !menuToggle) return;
    mobileNav.hidden = false;
    mobileNav.classList.add("is-open");
    menuToggle.setAttribute("aria-expanded", "true");
    menuToggle.setAttribute("aria-label", "Close navigation");
    if (backdrop) backdrop.hidden = false;
  }

  function closeMobileNav() {
    if (!mobileNav || !menuToggle) return;
    mobileNav.classList.remove("is-open");
    mobileNav.hidden = true;
    menuToggle.setAttribute("aria-expanded", "false");
    menuToggle.setAttribute("aria-label", "Open navigation");
    if (backdrop) backdrop.hidden = true;
  }

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;

    const goto = target.closest("[data-goto]");
    if (goto?.dataset.goto) {
      event.preventDefault();
      setActiveView(goto.dataset.goto);
      return;
    }

    const nav = target.closest(".nav-item[data-view]");
    if (nav?.dataset.view) {
      event.preventDefault();
      setActiveView(nav.dataset.view);
    }
  });

  menuToggle?.addEventListener("click", () => {
    const open = menuToggle.getAttribute("aria-expanded") === "true";
    if (open) closeMobileNav();
    else openMobileNav();
  });

  backdrop?.addEventListener("click", closeMobileNav);

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMobileNav();
  });

  setActiveView("home");
})();