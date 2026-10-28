/* Shared DOM helpers and components. Data is always inserted as text, never as HTML.
   Colours come from theme.css variables (classes), not from this file. */
const BRAND = "Parcelly";

const ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  chevron: '<path d="M9 6l6 6-6 6"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a1 1 0 0 1 1-1h10"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  truck: '<path d="M3 6h11v10H3zM14 9h4l3 3v4h-7"/><circle cx="7.5" cy="17.5" r="1.8"/><circle cx="17.5" cy="17.5" r="1.8"/>',
  box: '<path d="M12 3l8 4v10l-8 4-8-4V7zM4 7l8 4 8-4M12 11v10"/>',
  pin: '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  route: '<circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="6" r="2.5"/><path d="M8.5 18H15a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h6.5"/>',
  list: '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  share: '<path d="M12 15V4M8 8l4-4 4 4M5 13v6h14v-6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  home: '<path d="M4 11l8-7 8 7v9H4z"/>',
};

const STAGE_RANK = { BOOKED: 0, PICKED_UP: 1, IN_TRANSIT: 2, AT_BRANCH: 2, OUT_FOR_DELIVERY: 3, DELIVERED: 4 };
const CANONICAL = ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"];

const ui = {
  el(tag, props, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (k === "class") node.className = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else if (v !== false && v != null) node.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) node.append(c instanceof Node ? c : document.createTextNode(c ?? ""));
    return node;
  },
  $(sel, root = document) { return root.querySelector(sel); },
  clear(node) { node.replaceChildren(); return node; },

  /* Icon paths above are static trusted strings, so innerHTML is safe here. */
  icon(name) {
    const span = document.createElement("span");
    span.className = "ico";
    span.setAttribute("aria-hidden", "true");
    span.innerHTML = `<svg viewBox="0 0 24 24">${ICONS[name] || ""}</svg>`;
    return span;
  },

  message(node, text, kind = "error") {
    node.replaceChildren();
    if (!text) { node.hidden = true; return; }
    node.className = `msg ${kind}`;
    node.textContent = text;
    node.hidden = false;
  },

  label(status) {
    return status ? status.toLowerCase().split("_").map(w => w[0].toUpperCase() + w.slice(1)).join(" ") : "";
  },
  badge(status) {
    return status ? ui.el("span", { class: `badge ${status}` }, ui.label(status)) : "";
  },

  fmtTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
  },
  ago(iso) {
    const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (isNaN(mins)) return "";
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min ago`;
    if (mins < 2880) return `${Math.round(mins / 60)} h ago`;
    return `${Math.round(mins / 1440)} days ago`;
  },

  /* ---- tables ---- */
  table(container, columns, rows, emptyText = "Nothing to show.") {
    ui.clear(container);
    if (!rows || !rows.length) {
      container.append(ui.el("p", { class: "empty" }, emptyText));
      return;
    }
    const head = ui.el("tr", {}, columns.map(c => ui.el("th", {}, c.label)));
    const body = rows.map(r => ui.el("tr", {}, columns.map(c => {
      const v = c.render ? c.render(r) : r[c.key];
      return ui.el("td", {}, v ?? "");
    })));
    container.append(ui.el("div", { class: "table-wrap" },
      ui.el("table", {}, ui.el("thead", {}, head), ui.el("tbody", {}, body))));
  },
  autoTable(container, rows, emptyText) {
    const cols = rows && rows.length ? Object.keys(rows[0]).map(k => ({ key: k, label: k })) : [];
    ui.table(container, cols, rows, emptyText);
  },
  fill(select, items, valueKey, labelKey, placeholder) {
    ui.clear(select);
    if (placeholder) select.append(ui.el("option", { value: "" }, placeholder));
    for (const it of items) select.append(ui.el("option", { value: it[valueKey] }, it[labelKey]));
  },

  cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); },
  qs(name) { return new URLSearchParams(location.search).get(name); },

  /* ---- states ---- */
  skeleton(container, n = 3) {
    ui.clear(container);
    for (let i = 0; i < n; i++) container.append(ui.el("div", { class: "skeleton", "aria-hidden": "true" }));
  },
  emptyState(container, title, text, action) {
    ui.clear(container).append(ui.el("div", { class: "empty-state" },
      ui.el("img", { src: "/img/box.svg", alt: "" }),
      ui.el("h2", {}, title), ui.el("p", {}, text),
      action ? ui.el("a", { class: "button", href: action.href }, action.label) : ""));
  },
  toast(text) {
    const t = ui.el("div", { class: "msg ok toast", role: "status" }, text);
    document.body.append(t);
    setTimeout(() => t.remove(), 1800);
  },
  async copy(text, button) {
    try {
      await navigator.clipboard.writeText(text);
      ui.toast("Copied");
    } catch (e) {
      ui.toast("Copy is not available in this browser");
    }
  },

  /* ---- components ---- */
  searchBar({ onSubmit, placeholder = "Enter shipment ID (e.g. 10000)" }) {
    const input = ui.el("input", { type: "number", min: "1", required: true, placeholder, "aria-label": "Shipment ID" });
    const form = ui.el("form", { class: "search-bar", role: "search" },
      ui.icon("search"), input,
      ui.el("button", { type: "submit", "aria-label": "Track shipment" }, ui.icon("arrow")));
    form.addEventListener("submit", (e) => { e.preventDefault(); onSubmit(input.value); });
    return { form, input };
  },

  async tryLine(container, hrefFor) {
    try {
      const rows = await api.get("/api/shipments");
      if (!rows.length) return;
      container.append("Try:", ...rows.slice(0, 3).map(r => ui.el("a", { href: hrefFor(r.shipmentId) }, `#${r.shipmentId}`)));
    } catch (e) { /* optional hint */ }
  },

  progress(status) {
    const rank = status in STAGE_RANK ? STAGE_RANK[status] : (status === "DELAYED" ? 2 : 0);
    return ui.el("div", { class: `progress p${rank} ${status || ""}` }, ui.el("span", { class: "fill" }));
  },

  parcelCard(s) {
    return ui.el("a", { class: "parcel-card", href: `/track.html?id=${s.shipmentId}` },
      ui.el("img", { src: "/img/box.svg", alt: "" }),
      ui.el("div", {},
        ui.el("div", { class: "top" }, ui.el("span", { class: "id" }, `#${s.shipmentId}`), ui.badge(s.status || "BOOKED")),
        ui.el("div", { class: "meta" }, `${s.senderCity || s.sender} → ${s.receiverCity || s.receiver}`),
        ui.progress(s.status),
        ui.el("div", { class: "meta" }, s.place ? `Now at ${s.place} · Booked ${s.bookingDate}` : `Booked ${s.bookingDate}`)),
      ui.el("span", { class: "go" }, ui.icon("chevron")));
  },

  /* Timeline from real events; upcoming stages are only the standard statuses not reached yet. */
  timeline(container, journey, status) {
    ui.clear(container);
    const reached = journey.map(j => STAGE_RANK[j.status]).filter(r => r !== undefined);
    const top = reached.length ? Math.max(...reached) : -1;
    const done = status === "DELIVERED";
    const items = journey.map((j, i) => {
      const last = i === journey.length - 1;
      const state = last && !done ? "current" : "done";
      return ui.el("li", { class: `${state} ${last ? j.status : ""}` },
        ui.el("span", { class: "dot" }, state === "done" ? ui.icon("check") : ui.icon("truck")),
        ui.el("div", {}, ui.el("span", { class: "what" }, ui.label(j.status)),
          ui.el("span", { class: "when" }, ui.fmtTime(j.time)), ui.el("span", { class: "where" }, j.place)));
    });
    if (status !== "DELIVERED" && status !== "CANCELLED") {
      for (const s of CANONICAL.filter(s => STAGE_RANK[s] > top)) {
        items.push(ui.el("li", { class: "upcoming" },
          ui.el("span", { class: "dot" }, ui.icon("clock")),
          ui.el("div", {}, ui.el("span", { class: "what" }, ui.label(s)))));
      }
    }
    if (!items.length) container.append(ui.el("li", { class: "upcoming" }, ui.el("span", { class: "dot" }), "No tracking events yet."));
    else container.append(...items);
  },

  /* Schematic route of the real scan locations. This is NOT a geographic map or live GPS. */
  routeMap(container, { origin, stops, destination, delivered }) {
    ui.clear(container);
    const NS = "http://www.w3.org/2000/svg";
    const s = (tag, attrs = {}, text) => {
      const n = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
      if (text !== undefined) n.textContent = text;
      return n;
    };
    const places = [origin, ...stops, destination];
    const n = places.length;
    const cur = delivered ? n - 1 : stops.length;      // index of the last scan
    const pts = places.map((_, i) => ({ x: 80 + i * (440 / (n - 1)), y: 150 + 55 * Math.sin(i * 1.7) }));
    const svg = s("svg", { viewBox: "0 0 600 300", role: "img", "aria-label": `Route from ${origin} to ${destination}` });
    for (let i = 0; i < n - 1; i++) {
      const a = pts[i], b = pts[i + 1], mx = (a.x + b.x) / 2;
      svg.append(s("path", { class: i < cur ? "seg-done" : "seg-todo", d: `M${a.x} ${a.y} C${mx} ${a.y} ${mx} ${b.y} ${b.x} ${b.y}` }));
    }
    const words = (t) => {
      const w = t.split(" "), h = Math.ceil(w.length / 2);
      return w.length > 2 ? [w.slice(0, h).join(" "), w.slice(h).join(" ")] : [t];
    };
    places.forEach((name, i) => {
      const p = pts[i];
      const cls = i === 0 ? "origin" : (i === n - 1 ? "dest" : "stop");
      svg.append(s("circle", { class: cls, cx: p.x, cy: p.y, r: i === 0 || i === n - 1 ? 11 : 7 }));
      if (i === cur) {
        svg.append(s("rect", { class: "parcel", x: p.x - 16, y: p.y - 16, width: 32, height: 32, rx: 10 }));
        svg.append(s("path", { class: "glyph", d: `M${p.x} ${p.y - 8} l8 4 v8 l-8 4 l-8 -4 v-8z` }));
      }
      const above = p.y > 215;
      const lines = words(name);
      const t = s("text", { x: p.x, y: above ? p.y - 24 - (lines.length - 1) * 15 : p.y + 32 });
      lines.forEach((ln, k) => t.append(s("tspan", { x: p.x, dy: k === 0 ? 0 : 15 }, ln)));
      svg.append(t);
    });
    container.append(svg);
  },

  /* Map inputs from real shipment data: booking branch, distinct scan places, receiver city. */
  mapData(ship, journey) {
    const stops = [];
    let last = ship.bookedAt;
    for (const j of journey) {
      if (j.place !== last) { stops.push(j.place); last = j.place; }
    }
    return { origin: ship.bookedAt, stops, destination: ship.receiver.city, delivered: ship.status === "DELIVERED" };
  },
  etaCard(container, ship) {
    ui.clear(container);
    if (!ship.place) { container.append(ui.el("strong", {}, "No scans yet")); return; }
    container.append(
      ui.el("strong", {}, ship.status === "DELIVERED" ? `Delivered · ${ship.place}` : `Last scan: ${ship.place}`),
      ui.el("span", { class: "muted" }, `${ui.label(ship.status)} · ${ui.ago(ship.since)}`));
  },

  /* ---- page chrome ---- */
  async init({ staffOnly = false } = {}) {
    let user;
    try { user = await api.get("/api/auth/me"); } catch (e) { return null; }
    if (staffOnly && user.role !== "STAFF") {
      location.href = "/home.html";
      return null;
    }
    const staff = user.role === "STAFF";
    const items = [
      ["/home.html", "Home"], ["/track.html", "Track"], ["/parcels.html", staff ? "All Parcels" : "My Parcels"],
      ["/book.html", "Send"], ["/route.html", "Routes"],
      ...(staff ? [["/hub.html", "Hub impact"], ["/reports.html", "Reports"], ["/customers.html", "Customers"], ["/dashboard.html", "Dashboard"]]
                : [["/dashboard.html", "Profile"]]),
    ];
    const nav = ui.el("nav", { class: "site-nav", id: "site-nav", "aria-label": "Main" },
      items.map(([href, label]) => ui.el("a", { href, "aria-current": location.pathname === href ? "page" : false }, label)));
    const toggle = ui.el("button", { class: "icon nav-toggle", type: "button", "aria-label": "Menu", "aria-expanded": "false", "aria-controls": "site-nav",
      onclick: () => { const open = nav.classList.toggle("open"); toggle.setAttribute("aria-expanded", String(open)); } }, ui.icon("menu"));
    const menu = ui.el("details", { class: "user-menu" },
      ui.el("summary", { "aria-label": "Account menu" }, ui.el("span", { class: "avatar" }, (user.name || "?")[0].toUpperCase())),
      ui.el("div", { class: "menu-panel" },
        ui.el("p", {}, ui.el("strong", {}, user.name), ui.el("br"), ui.el("span", { class: "muted small" }, `${user.role} · ${user.email}`)),
        ui.el("button", { class: "secondary", type: "button", onclick: async () => {
          await api.post("/api/auth/logout");
          location.href = "/login.html";
        } }, "Log out")));
    document.body.prepend(ui.el("header", { class: "site-header" },
      ui.el("div", { class: "inner" },
        ui.el("a", { class: "brand", href: "/home.html" }, ui.el("img", { src: "/img/logo.svg", alt: "" }), BRAND),
        nav, toggle, menu)));
    return user;
  },

  /* vis-network helper (used for the G1 graph view and the hub network). */
  graph(container, data, options = {}) {
    if (typeof vis === "undefined") {
      container.textContent = "Graph library could not be loaded.";
      return null;
    }
    const text = ui.cssVar("--c-text"), border = ui.cssVar("--c-border"), muted = ui.cssVar("--c-muted");
    const group = (c) => ({ color: { background: c, border: c }, font: { color: text } });
    return new vis.Network(container, {
      nodes: new vis.DataSet(data.nodes),
      edges: new vis.DataSet(data.edges),
    }, {
      nodes: { shape: "dot", size: 16, font: { color: text, size: 13 } },
      edges: { color: { color: border, highlight: ui.cssVar("--c-coral") }, arrows: "to",
               font: { color: muted, size: 11, strokeWidth: 0, align: "middle" }, smooth: { type: "dynamic" } },
      groups: {
        Shipment: group(ui.cssVar("--c-shipment")), TrackingEvent: group(ui.cssVar("--c-event")),
        BRANCH: group(ui.cssVar("--c-branch")), HUB: group(ui.cssVar("--c-hub")), Branch: group(ui.cssVar("--c-branch")),
      },
      physics: { stabilization: { iterations: 150 } },
      ...options,
    });
  },
};
