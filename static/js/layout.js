/* One source of truth for the header. Every page calls Layout.boot(); no page writes its own nav. */
const NAV = {
  STAFF: [["Overview", "/", "home"], ["Shipments", "/shipments", "box"], ["Network", "/network", "route"],
          ["Customers", "/customers", "user"], ["Reports", "/reports", "list"]],
  CUSTOMER: [["Home", "/", "home"], ["My parcels", "/shipments", "box"]],
};
const PRIMARY = {
  STAFF: { label: "New shipment", href: "/shipments/new" },
  CUSTOMER: { label: "Send a parcel", href: "/shipments/new" },
};

const Layout = {
  user: null,

  isActive(href) {
    const p = location.pathname;
    return href === "/" ? p === "/" : p === href || p.startsWith(href + "/");
  },

  /* Pages put their content in <main id="main">. Returns the logged-in user. */
  async boot() {
    let user;
    try { user = await api.get("/api/auth/me"); } catch (e) { return null; }
    Layout.user = user;
    const items = NAV[user.role];

    const nav = ui.el("nav", { class: "site-nav", "aria-label": "Main" }, items.map(([label, href, icon]) =>
      ui.el("a", { href, "aria-current": Layout.isActive(href) ? "page" : false }, ui.el("span", { class: "nav-ico" }, ui.icon(icon)), label)));

    const input = ui.el("input", { type: "search", placeholder: "Shipment ID", "aria-label": "Search by shipment ID", autocomplete: "off", enterkeyhint: "search" });
    const search = ui.el("form", { class: "head-search", role: "search", "aria-label": "Search shipments" }, input,
      ui.el("button", { type: "submit", "aria-label": "Search" }, ui.icon("search")));
    search.addEventListener("submit", (e) => {
      e.preventDefault();
      const v = input.value.trim().replace(/^#/, "");
      if (!v) return;
      location.href = /^\d+$/.test(v) ? `/shipments/${v}` : `/shipments?q=${encodeURIComponent(v)}`;
    });

    const primary = PRIMARY[user.role];
    const cta = ui.el("a", { class: "button head-primary", href: primary.href, "aria-label": primary.label },
      ui.icon("plus"), ui.el("span", { class: "label-long" }, primary.label));

    const menu = ui.el("details", { class: "user-menu" },
      ui.el("summary", { "aria-label": `Account menu for ${user.name}` }, ui.el("span", { class: "avatar" }, (user.name || "?")[0].toUpperCase())),
      ui.el("div", { class: "menu-panel" },
        ui.el("div", { class: "who" }, ui.el("strong", {}, `${user.name}${user.lastName ? " " + user.lastName : ""}`), ui.el("br"),
          ui.el("span", { class: "muted small" }, user.role === "STAFF" ? "Staff" : "Customer")),
        ui.el("a", { href: "/account", role: "menuitem" }, ui.icon("user"), "Account"),
        ui.el("button", { type: "button", role: "menuitem", onclick: async () => { await api.post("/api/auth/logout"); location.href = "/login"; } }, ui.icon("arrow"), "Log out")));
    ui.$(".menu-panel", menu).setAttribute("role", "menu");
    menu.addEventListener("toggle", () => { if (menu.open) ui.$("[role=menuitem]", menu).focus(); });
    menu.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && menu.open) { menu.open = false; ui.$("summary", menu).focus(); return; }
      const items = ui.$$("[role=menuitem]", menu), i = items.indexOf(document.activeElement);
      if (menu.open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
        e.preventDefault();
        items[(i + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length].focus();
      }
    });
    document.addEventListener("click", (e) => { if (menu.open && !menu.contains(e.target)) menu.open = false; });

    document.body.prepend(
      ui.el("a", { class: "skip-link", href: "#main" }, "Skip to content"),
      ui.el("header", { class: "site-header" }, ui.el("div", { class: "inner" },
        ui.el("a", { class: "brand", href: "/" }, ui.el("img", { src: "/img/logo.svg", alt: "" }), BRAND),
        nav, search, cta, menu)));
    ui.$$(".crumb").forEach(c => { if (!ui.$(".ico", c)) c.prepend(ui.icon("back")); });
    let flash = null;
    try { flash = sessionStorage.getItem("flash"); sessionStorage.removeItem("flash"); } catch (e) { /* storage blocked */ }
    if (flash) ui.toast(flash);
    return user;
  },
};
