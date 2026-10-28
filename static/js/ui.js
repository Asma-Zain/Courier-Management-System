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
  share: '<path d="M12 15V4M8 8l4-4 4 4M5 13v6h14v-6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  home: '<path d="M4 11l8-7 8 7v9H4z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  alert: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.5h.01"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  print: '<path d="M7 9V4h10v5M7 17H5a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-2M7 14h10v6H7z"/>',
  download: '<path d="M12 4v11M7 11l5 5 5-5M5 20h14"/>',
  swap: '<path d="M7 4L3 8l4 4M3 8h14M17 20l4-4-4-4M21 16H7"/>',
  zoomIn: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5M11 8v6M8 11h6"/>',
  zoomOut: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5M8 11h6"/>',
  fit: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  reset: '<path d="M4 12a8 8 0 1 0 3-6.2M4 4v5h5"/>',
};

const STATUS = {
  BOOKED: { label: "Booked", icon: "box" }, PICKED_UP: { label: "Picked up", icon: "box" },
  IN_TRANSIT: { label: "In transit", icon: "truck" }, AT_BRANCH: { label: "At branch", icon: "pin" },
  OUT_FOR_DELIVERY: { label: "Out for delivery", icon: "truck" }, DELIVERED: { label: "Delivered", icon: "check" },
  DELAYED: { label: "Delayed", icon: "alert" }, CANCELLED: { label: "Cancelled", icon: "x" },
};
const PAYMENT = {
  PAID: { label: "Paid", icon: "check" }, PARTIAL: { label: "Partly paid", icon: "clock" },
  UNPAID: { label: "Unpaid", icon: "alert" }, PENDING: { label: "Pending", icon: "clock" },
};
const STAGE_RANK = { BOOKED: 0, PICKED_UP: 1, IN_TRANSIT: 2, AT_BRANCH: 2, OUT_FOR_DELIVERY: 3, DELIVERED: 4 };
const CANONICAL = ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"];

const TZ = "Asia/Kolkata";
const DATE_FMT = new Intl.DateTimeFormat("en-IN", { timeZone: TZ, day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true });
const DAY_FMT = new Intl.DateTimeFormat("en-IN", { timeZone: TZ, day: "numeric", month: "short", year: "numeric" });
const MONEY0 = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 0, maximumFractionDigits: 0 });
const MONEY2 = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2, maximumFractionDigits: 2 });

const ui = {
  /* ---------------- DOM ---------------- */
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
  $$(sel, root = document) { return [...root.querySelectorAll(sel)]; },
  clear(node) { node.replaceChildren(); return node; },
  qs(name) { return new URLSearchParams(location.search).get(name); },
  cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); },
  /* Icon paths above are static trusted strings, so innerHTML is safe here. */
  icon(name) {
    const span = document.createElement("span");
    span.className = "ico";
    span.setAttribute("aria-hidden", "true");
    span.innerHTML = `<svg viewBox="0 0 24 24">${ICONS[name] || ""}</svg>`;
    return span;
  },
  debounce(fn, ms = 400) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; },

  /* ---------------- formats (one date format, one currency format) ---------------- */
  fmtDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return isNaN(d) ? String(iso) : DATE_FMT.format(d).replace(/\bam\b/i, "am").replace(/\bpm\b/i, "pm");
  },
  fmtDay(iso) {
    if (!iso) return "";
    const d = new Date(String(iso).length === 10 ? iso + "T00:00:00+05:30" : iso);
    return isNaN(d) ? String(iso) : DAY_FMT.format(d);
  },
  fmtMoney(n) { return n === null || n === undefined ? "" : (Number.isInteger(n) ? MONEY0 : MONEY2).format(n); },
  fmtNum(n) { return n === null || n === undefined ? "" : Number(n).toLocaleString("en-IN"); },
  ago(iso) {
    const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (isNaN(mins)) return "";
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min ago`;
    if (mins < 2880) return `${Math.round(mins / 60)} h ago`;
    return `${Math.round(mins / 1440)} days ago`;
  },
  /* <time> with the absolute Indian-time date in the tooltip */
  timeAgo(iso) {
    return ui.el("time", { datetime: iso, title: ui.fmtDate(iso) }, ui.ago(iso));
  },
  timeAbs(iso) { return ui.el("time", { datetime: iso, title: ui.ago(iso) }, ui.fmtDate(iso)); },
  statusLabel(s) { return (STATUS[s] || { label: s || "" }).label; },

  /* ---------------- chips ---------------- */
  badge(status) {
    const s = STATUS[status];
    return s ? ui.el("span", { class: `badge ${status}` }, ui.icon(s.icon), s.label) : "";
  },
  payBadge(state) {
    const s = PAYMENT[state];
    return s ? ui.el("span", { class: `badge ${state}` }, ui.icon(s.icon), s.label) : "";
  },

  /* ---------------- feedback ---------------- */
  toast(text, kind = "ok") {
    let stack = ui.$(".toast-stack");
    if (!stack) { stack = ui.el("div", { class: "toast-stack", role: "status", "aria-live": "polite" }); document.body.append(stack); }
    const t = ui.el("div", { class: `msg ${kind} toast` }, text);
    stack.append(t);
    setTimeout(() => t.remove(), 3200);
  },
  /* A visible error area next to the action; moves focus there. */
  formError(box, text) {
    box.textContent = text || "";
    box.hidden = !text;
    if (text) { box.setAttribute("tabindex", "-1"); box.scrollIntoView({ block: "center" }); box.focus({ preventScroll: true }); }
  },
  setError(control, text) {
    const wrap = control.closest("label") || control.parentElement;
    let err = ui.$(".field-error", wrap);
    if (!text) { if (err) err.remove(); control.removeAttribute("aria-invalid"); control.removeAttribute("aria-describedby"); return; }
    if (!err) {
      err = ui.el("p", { class: "field-error", role: "alert", id: `err-${Math.random().toString(36).slice(2, 8)}` });
      wrap.append(err);
    }
    err.textContent = text;
    control.setAttribute("aria-invalid", "true");
    control.setAttribute("aria-describedby", err.id);
  },
  /* rules: [[control, (value) => message|null], ...]. Focuses and scrolls to the first error. */
  check(rules) {
    let first = null;
    for (const [control, test] of rules) {
      const msg = test(control.value.trim());
      ui.setError(control, msg);
      if (msg && !first) first = control;
    }
    if (first) { first.scrollIntoView({ block: "center" }); first.focus({ preventScroll: true }); }
    return !first;
  },
  field(labelText, control, { required = false, hint = "" } = {}) {
    return ui.el("label", {}, ui.el("span", {}, labelText, required ? ui.el("span", { class: "req", "aria-hidden": "true" }, " *") : ""),
      control, hint ? ui.el("span", { class: "hint" }, hint) : "");
  },
  message(node, text, kind = "error") {
    node.replaceChildren();
    if (!text) { node.hidden = true; return; }
    node.className = `msg ${kind}`;
    node.textContent = text;
    node.hidden = false;
  },

  /* ---------------- dialogs ---------------- */
  dialog({ title, body, actions = [], onClose }) {
    const dlg = ui.el("dialog", { "aria-labelledby": "dlg-title" }, ui.el("h2", { id: "dlg-title" }, title), body,
      actions.length ? ui.el("div", { class: "dialog-actions" }, actions.map(a =>
        ui.el("button", { type: a.submit ? "submit" : "button", class: a.kind || "", form: a.form, onclick: a.onClick || (() => dlg.close()) }, a.label))) : "");
    dlg.addEventListener("close", () => { dlg.remove(); if (onClose) onClose(); });
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    document.body.append(dlg);
    dlg.showModal();
    return dlg;
  },
  confirm({ title, message, confirmLabel = "Confirm", danger = false }) {
    return new Promise((resolve) => {
      let answer = false;
      ui.dialog({
        title, body: ui.el("p", {}, message),
        actions: [{ label: "Cancel", kind: "secondary", onClick: (e) => e.target.closest("dialog").close() },
                  { label: confirmLabel, kind: danger ? "danger-solid" : "", onClick: (e) => { answer = true; e.target.closest("dialog").close(); } }],
        onClose: () => resolve(answer),
      });
    });
  },

  /* ---------------- tabs (ARIA, arrow keys) ---------------- */
  tabs(container, tabs, onSelect, initial) {
    const list = ui.el("div", { class: "tabs", role: "tablist" });
    const buttons = tabs.map(t => ui.el("button", { class: "tab", type: "button", role: "tab", id: `tab-${t.id}`, "aria-controls": `panel-${t.id}` }, t.label));
    function select(id, focus = false) {
      tabs.forEach((t, i) => {
        const on = t.id === id;
        buttons[i].setAttribute("aria-selected", String(on));
        buttons[i].tabIndex = on ? 0 : -1;
        const panel = document.getElementById(`panel-${t.id}`);
        if (panel) panel.hidden = !on;
        if (on && focus) buttons[i].focus();
      });
      onSelect(id);
    }
    buttons.forEach((b, i) => {
      b.addEventListener("click", () => select(tabs[i].id));
      b.addEventListener("keydown", (e) => {
        const move = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        if (move) { e.preventDefault(); select(tabs[(i + move + tabs.length) % tabs.length].id, true); }
        if (e.key === "Home") { e.preventDefault(); select(tabs[0].id, true); }
        if (e.key === "End") { e.preventDefault(); select(tabs[tabs.length - 1].id, true); }
      });
    });
    ui.clear(container).append(list);
    list.append(...buttons);
    select(initial || tabs[0].id);
    return { select };
  },

  /* ---------------- lists, tables, states ---------------- */
  skeleton(container, n = 3) {
    ui.clear(container);
    for (let i = 0; i < n; i++) container.append(ui.el("div", { class: "skeleton", "aria-hidden": "true" }));
    container.setAttribute("aria-busy", "true");
  },
  emptyState(container, title, text, action) {
    container.removeAttribute("aria-busy");
    ui.clear(container).append(ui.el("div", { class: "empty-state" },
      ui.el("img", { src: "/img/box.svg", alt: "" }),
      ui.el("h2", {}, title), ui.el("p", {}, text),
      action ? ui.el("a", { class: "button", href: action.href }, action.label) : ""));
  },
  errorState(container, text, retry) {
    container.removeAttribute("aria-busy");
    ui.clear(container).append(ui.el("div", { class: "empty-state" },
      ui.el("h2", {}, "Could not load this"), ui.el("p", {}, text),
      retry ? ui.el("button", { type: "button", onclick: retry }, "Try again") : ""));
  },
  /* columns: [{key, label, num?, render?(row)}]; rows open `href(row)` when clicked. Cards on mobile. */
  table(container, columns, rows, { empty = "Nothing to show.", href } = {}) {
    container.removeAttribute("aria-busy");
    ui.clear(container);
    if (!rows || !rows.length) { container.append(ui.el("p", { class: "empty" }, empty)); return; }
    const head = ui.el("tr", {}, columns.map(c => ui.el("th", { scope: "col", class: c.num ? "num" : "" }, c.label)));
    const body = rows.map(r => {
      const tr = ui.el("tr", { class: href ? "clickable" : "" }, columns.map(c =>
        ui.el("td", { "data-label": c.label, class: c.num ? "num" : "" }, c.render ? c.render(r) : (r[c.key] ?? ""))));
      if (href) tr.addEventListener("click", (e) => { if (!e.target.closest("a,button")) location.href = href(r); });
      return tr;
    });
    container.append(ui.el("div", { class: "table-wrap" }, ui.el("table", { class: "data" }, ui.el("thead", {}, head), ui.el("tbody", {}, body))));
  },
  fill(select, items, valueKey, labelKey, placeholder) {
    ui.clear(select);
    if (placeholder) select.append(ui.el("option", { value: "" }, placeholder));
    for (const it of items) select.append(ui.el("option", { value: it[valueKey] }, it[labelKey]));
  },
  pager(container, { page, pageSize, total }, go) {
    ui.clear(container);
    const pages = Math.max(1, Math.ceil(total / pageSize));
    if (total <= pageSize) return;
    container.append(ui.el("div", { class: "pager" },
      ui.el("span", { class: "muted small" }, `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}`),
      ui.el("div", { class: "row" },
        ui.el("button", { class: "secondary", type: "button", disabled: page <= 1, onclick: () => go(page - 1) }, "Previous"),
        ui.el("span", { class: "small" }, `Page ${page} of ${pages}`),
        ui.el("button", { class: "secondary", type: "button", disabled: page >= pages, onclick: () => go(page + 1) }, "Next"))));
  },

  /* Cell formatting driven by the report catalogue (friendly formats, not raw aliases). */
  cell(format, value) {
    if (value === null || value === undefined) return "";
    switch (format) {
      case "int": return ui.fmtNum(value);
      case "money": return ui.fmtMoney(value);
      case "kg": return `${ui.fmtNum(value)} kg`;
      case "hours": return `${ui.fmtNum(value)} h`;
      case "date": return ui.fmtDay(value);
      case "kind": return value === "HUB" ? "Hub" : "Branch";
      case "shipment": return ui.el("a", { href: `/shipments/${value}` }, `#${value}`);
      default: return String(value);
    }
  },
  csv(filename, columns, rows) {
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const text = [columns.map(c => esc(c.label)).join(","), ...rows.map(r => columns.map(c => esc(r[c.key])).join(","))].join("\r\n");
    const a = ui.el("a", { href: URL.createObjectURL(new Blob([text], { type: "text/csv" })), download: filename });
    document.body.append(a); a.click(); a.remove();
  },
  barChart(container, rows, { label, value, format }) {
    ui.clear(container);
    if (!rows.length) return;
    const NS = "http://www.w3.org/2000/svg", rowH = 30, labelW = 190, barW = 300;
    const max = Math.max(...rows.map(r => Number(r[value]) || 0), 1);
    const s = (tag, attrs, text) => { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); if (text !== undefined) n.textContent = text; return n; };
    const svg = s("svg", { class: "bar-chart", viewBox: `0 0 620 ${rows.length * rowH + 8}`, role: "img", "aria-label": "Bar chart" });
    rows.forEach((r, i) => {
      const y = i * rowH + 4, w = Math.max(2, (Number(r[value]) || 0) / max * barW);
      svg.append(s("text", { x: labelW - 8, y: y + 17, "text-anchor": "end" }, String(r[label]).slice(0, 26)));
      svg.append(s("rect", { class: "bar", x: labelW, y, width: w, height: 20, rx: 6 }));
      const txt = ui.cell(format, r[value]);
      svg.append(s("text", { class: "val", x: labelW + w + 8, y: y + 16 }, typeof txt === "string" ? txt : String(r[value])));
    });
    container.append(svg);
  },

  async copy(text) {
    try { await navigator.clipboard.writeText(text); ui.toast("Copied"); }
    catch (e) { ui.toast("Copy is not available in this browser", "error"); }
  },

  /* ---------------- shipment components ---------------- */
  shipmentColumns() {
    return [
      { key: "shipmentId", label: "ID", render: r => ui.el("a", { href: `/shipments/${r.shipmentId}` }, `#${r.shipmentId}`) },
      { key: "parties", label: "Sender → Receiver", render: r => `${r.sender} → ${r.receiver}` },
      { key: "shipmentType", label: "Type", render: r => r.shipmentType[0] + r.shipmentType.slice(1).toLowerCase() },
      { key: "status", label: "Status", render: r => ui.badge(r.status) },
      { key: "place", label: "Now at" },
      { key: "bookingDate", label: "Booked", render: r => ui.fmtDay(r.bookingDate) },
      { key: "totalAmount", label: "Amount", num: true, render: r => ui.fmtMoney(r.totalAmount) },
      { key: "paymentState", label: "Payment", render: r => ui.payBadge(r.paymentState === "PARTIAL" ? "PARTIAL" : (r.paymentState === "PAID" ? "PAID" : "UNPAID")) },
    ];
  },
  progress(status) {
    const rank = status in STAGE_RANK ? STAGE_RANK[status] : (status === "DELAYED" ? 2 : 0);
    return ui.el("div", { class: `progress p${rank} ${status || ""}`, role: "presentation" }, ui.el("span", { class: "fill" }));
  },
  parcelCard(s) {
    return ui.el("a", { class: "parcel-card", href: `/shipments/${s.shipmentId}` },
      ui.el("img", { src: "/img/box.svg", alt: "" }),
      ui.el("div", {},
        ui.el("div", { class: "top" }, ui.el("span", { class: "id" }, `#${s.shipmentId}`), ui.badge(s.status)),
        ui.el("div", { class: "meta" }, `${s.senderCity} → ${s.receiverCity}`),
        ui.progress(s.status),
        ui.el("div", { class: "meta" }, s.place ? `Now at ${s.place} · Booked ${ui.fmtDay(s.bookingDate)}` : `Booked ${ui.fmtDay(s.bookingDate)}`)),
      ui.el("span", { class: "go" }, ui.icon("chevron")));
  },
  /* Timeline from real events. A missing BOOKED step is synthesised from the booking date.
     Upcoming steps are only the standard statuses not reached yet, with no invented times. */
  timeline(container, journey, status, { bookingDate, bookedAt } = {}) {
    ui.clear(container);
    const events = journey.slice();
    if (!events.length || events[0].status !== "BOOKED") {
      events.unshift({ status: "BOOKED", time: null, date: bookingDate, place: bookedAt, synthetic: true });
    }
    const reached = events.map(j => STAGE_RANK[j.status]).filter(r => r !== undefined);
    const top = Math.max(...reached);
    const done = status === "DELIVERED" || status === "CANCELLED";
    const items = events.map((j, i) => {
      const last = i === events.length - 1;
      const state = last && !done ? "current" : "done";
      return ui.el("li", { class: `${state} ${last ? j.status : ""}` },
        ui.el("span", { class: "dot" }, ui.icon(state === "done" ? "check" : (STATUS[j.status] || {}).icon || "truck")),
        ui.el("div", {}, ui.el("span", { class: "what" }, ui.statusLabel(j.status)),
          ui.el("span", { class: "when" }, j.time ? ui.timeAbs(j.time) : `${ui.fmtDay(j.date)} (booking date)`),
          ui.el("span", { class: "where" }, j.place + (j.loggedBy ? ` · by ${j.loggedBy}` : "")),
          j.note ? ui.el("span", { class: "note" }, `“${j.note}”`) : ""));
    });
    if (!done) {
      for (const s of CANONICAL.filter(s => STAGE_RANK[s] > top)) {
        items.push(ui.el("li", { class: "upcoming" }, ui.el("span", { class: "dot" }, ui.icon("clock")),
          ui.el("div", {}, ui.el("span", { class: "what" }, ui.statusLabel(s)))));
      }
    }
    container.append(...items);
  },
  mapData(ship, journey) {
    const stops = [];
    let last = ship.bookedAt;
    for (const j of journey) if (j.place !== last) { stops.push(j.place); last = j.place; }
    return { origin: ship.bookedAt, stops, destination: ship.receiver.city, delivered: ship.status === "DELIVERED" };
  },
  /* Schematic route of the real scan locations. This is NOT a geographic map or live GPS. */
  routeMap(container, { origin, stops, destination, delivered }) {
    ui.clear(container);
    const NS = "http://www.w3.org/2000/svg";
    const s = (tag, attrs = {}, text) => { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); if (text !== undefined) n.textContent = text; return n; };
    const places = [origin, ...stops, destination];
    const n = places.length;
    const cur = delivered ? n - 1 : stops.length;
    const pts = places.map((_, i) => ({ x: 80 + i * (440 / (n - 1)), y: 150 + 55 * Math.sin(i * 1.7) }));
    const svg = s("svg", { viewBox: "0 0 600 300", role: "img", "aria-label": `Route from ${origin} to ${destination}` });
    for (let i = 0; i < n - 1; i++) {
      const a = pts[i], b = pts[i + 1], mx = (a.x + b.x) / 2;
      svg.append(s("path", { class: i < cur ? "seg-done" : "seg-todo", d: `M${a.x} ${a.y} C${mx} ${a.y} ${mx} ${b.y} ${b.x} ${b.y}` }));
    }
    const words = (t) => { const w = t.split(" "), h = Math.ceil(w.length / 2); return w.length > 2 ? [w.slice(0, h).join(" "), w.slice(h).join(" ")] : [t]; };
    places.forEach((name, i) => {
      const p = pts[i];
      svg.append(s("circle", { class: i === 0 ? "origin" : (i === n - 1 ? "dest" : "stop"), cx: p.x, cy: p.y, r: i === 0 || i === n - 1 ? 11 : 7 }));
      if (i === cur) {
        svg.append(s("rect", { class: "parcel", x: p.x - 16, y: p.y - 16, width: 32, height: 32, rx: 10 }));
        svg.append(s("path", { class: "glyph", d: `M${p.x} ${p.y - 8} l8 4 v8 l-8 4 l-8 -4 v-8z` }));
      }
      const lines = words(name), above = p.y > 215;
      const t = s("text", { x: p.x, y: above ? p.y - 24 - (lines.length - 1) * 15 : p.y + 32 });
      lines.forEach((ln, k) => t.append(s("tspan", { x: p.x, dy: k === 0 ? 0 : 15 }, ln)));
      svg.append(t);
    });
    container.append(svg);
  },

  /* ---------------- graph (vis-network, vendored) ---------------- */
  graph(container, data, options = {}) {
    if (typeof vis === "undefined") { container.textContent = "Graph library could not be loaded."; return null; }
    const text = ui.cssVar("--c-text"), border = ui.cssVar("--c-border"), bg = ui.cssVar("--c-bg");
    const group = (c) => ({ color: { background: c, border: c, highlight: { background: c, border: ui.cssVar("--c-coral") } } });
    const net = new vis.Network(container, { nodes: new vis.DataSet(data.nodes), edges: new vis.DataSet(data.edges) }, {
      nodes: { shape: "dot", size: 16, font: { color: text, size: 14, strokeWidth: 4, strokeColor: bg } },
      edges: { color: { color: border, highlight: ui.cssVar("--c-coral"), hover: ui.cssVar("--c-peach") }, arrows: "to", width: 2,
               font: { color: ui.cssVar("--c-text-2"), size: 12, strokeWidth: 5, strokeColor: bg, align: "middle" },
               smooth: { type: "continuous" }, selectionWidth: 3 },
      groups: { Shipment: group(ui.cssVar("--c-shipment")), TrackingEvent: group(ui.cssVar("--c-event")),
                BRANCH: group(ui.cssVar("--c-branch")), HUB: group(ui.cssVar("--c-hub")), Branch: group(ui.cssVar("--c-branch")) },
      interaction: { hover: true, tooltipDelay: 150, navigationButtons: false },
      ...options,
    });
    const wrap = container.parentElement;
    if (wrap && wrap.classList.contains("graph-wrap") && !ui.$(".graph-tools", wrap)) {
      const tool = (icon, label, fn) => ui.el("button", { type: "button", "aria-label": label, title: label, onclick: fn }, ui.icon(icon));
      wrap.append(ui.el("div", { class: "graph-tools" },
        tool("zoomIn", "Zoom in", () => net.moveTo({ scale: net.getScale() * 1.25, animation: true })),
        tool("zoomOut", "Zoom out", () => net.moveTo({ scale: net.getScale() / 1.25, animation: true })),
        tool("fit", "Fit to screen", () => net.fit({ animation: true })),
        tool("reset", "Reset view", () => { net.fit(); net.unselectAll(); })));
    }
    net.once("stabilizationIterationsDone", () => net.fit());
    return net;
  },
};
