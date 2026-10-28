/* Small DOM helpers shared by every page. Data is always inserted as text, never as HTML. */
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

  message(node, text, kind = "error") {
    node.replaceChildren();
    if (!text) { node.hidden = true; return; }
    node.className = `msg ${kind}`;
    node.textContent = text;
    node.hidden = false;
  },

  badge(status) {
    return status ? ui.el("span", { class: `badge ${status}` }, status) : "";
  },

  /* columns: [{key, label, render?(row) -> string|Node}] */
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

  /* Auto columns from the keys of the first row. */
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

  /* Guard + header. Returns the logged-in user. */
  async init({ staffOnly = false } = {}) {
    let user;
    try { user = await api.get("/api/auth/me"); } catch (e) { return null; }
    if (staffOnly && user.role !== "STAFF") {
      location.href = "/dashboard.html";
      return null;
    }
    const items = [
      ["/dashboard.html", "Dashboard", false],
      ["/track.html", "Track", false],
      ["/book.html", "Book shipment", false],
      ["/route.html", "Routes", false],
      ["/hub.html", "Hub impact", true],
      ["/reports.html", "Reports", true],
      ["/customers.html", "Customers", true],
    ].filter(([, , staff]) => !staff || user.role === "STAFF");
    const nav = ui.el("nav", { class: "site-nav", "aria-label": "Main" },
      items.map(([href, label]) =>
        ui.el("a", { href, "aria-current": location.pathname === href ? "page" : false }, label)));
    const logout = ui.el("button", { class: "secondary", type: "button", onclick: async () => {
      await api.post("/api/auth/logout");
      location.href = "/login.html";
    } }, "Log out");
    const header = ui.el("header", { class: "site-header" },
      ui.el("div", { class: "inner" },
        ui.el("a", { class: "brand", href: "/dashboard.html" }, "Courier Tracking"),
        nav,
        ui.el("div", { class: "user-chip" }, `${user.name} · ${user.role}`, logout)));
    document.body.prepend(header);
    return user;
  },

  /* vis-network helpers: colours come from theme.css variables. */
  graph(container, data, options = {}) {
    if (typeof vis === "undefined") {
      container.textContent = "Graph library could not be loaded.";
      return null;
    }
    const text = ui.cssVar("--c-text"), border = ui.cssVar("--c-border"), muted = ui.cssVar("--c-muted");
    const group = (c) => ({ color: { background: c, border: c }, font: { color: text } });
    const net = new vis.Network(container, {
      nodes: new vis.DataSet(data.nodes),
      edges: new vis.DataSet(data.edges),
    }, {
      nodes: { shape: "dot", size: 16, font: { color: text, size: 13 } },
      edges: { color: { color: border, highlight: ui.cssVar("--c-accent") }, arrows: "to",
               font: { color: muted, size: 11, strokeWidth: 0, align: "middle" }, smooth: { type: "dynamic" } },
      groups: {
        Shipment: group(ui.cssVar("--c-shipment")),
        TrackingEvent: group(ui.cssVar("--c-event")),
        BRANCH: group(ui.cssVar("--c-branch")),
        HUB: group(ui.cssVar("--c-hub")),
        Branch: group(ui.cssVar("--c-branch")),
      },
      physics: { stabilization: { iterations: 150 } },
      ...options,
    });
    return net;
  },
};
