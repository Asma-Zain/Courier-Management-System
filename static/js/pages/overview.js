(async function () {
  const user = await Layout.boot();
  if (!user) return;
  const msg = ui.$("#msg");

  const FRIENDLY = { Customer: "Customers", Employee: "Employees", Branch: "Branches and hubs", Shipment: "Shipments",
                     Package: "Packages", Payment: "Payments", TrackingEvent: "Tracking events" };
  const tile = (href, num, label, cls = "") =>
    ui.el("a", { class: `kpi ${cls}`, href }, ui.el("span", { class: "num" }, num), ui.el("span", { class: "lbl" }, label));

  try {
    const [o, net] = await Promise.all([api.get("/api/overview"), api.get("/api/graph/network")]);
    const k = o.kpis;
    ui.clear(ui.$("#kpis")).removeAttribute("aria-busy");
    ui.$("#kpis").append(
      tile("/shipments?status=ACTIVE", ui.fmtNum(k.active), "Active shipments"),
      tile("/shipments?status=DELAYED", ui.fmtNum(k.delayed), "Delayed", k.delayed ? "warn" : ""),
      tile("/shipments?status=OUT_FOR_DELIVERY", ui.fmtNum(k.outForDelivery), "Out for delivery"),
      tile("/shipments?status=DELIVERED", ui.fmtNum(k.delivered), "Delivered", "ok"),
      tile("/shipments?payment=UNPAID", ui.fmtMoney(k.outstanding), "Outstanding payments", "money"));

    const att = ui.$("#attention");
    if (!o.attention.length) ui.emptyState(att, "All clear", "No delayed or unpaid shipments.");
    else att.append(ui.el("ul", { class: "list" }, o.attention.map(a => ui.el("li", {},
      ui.el("div", { class: "main" }, ui.el("a", { href: `/shipments/${a.shipmentId}` }, `#${a.shipmentId}`), ` · ${a.receiver}`,
        ui.el("span", { class: "sub" }, a.delayed ? `Delayed at ${a.place}` : "Awaiting payment")),
      a.delayed ? ui.badge("DELAYED") : ui.el("span", { class: "badge UNPAID" }, ui.fmtMoney(a.outstanding) + " due")))));

    const rec = ui.$("#recent");
    if (!o.recent.length) ui.emptyState(rec, "No activity yet", "Tracking events will appear here.");
    else rec.append(ui.el("ul", { class: "list" }, o.recent.map(r => ui.el("li", {},
      ui.el("div", { class: "main" }, ui.el("a", { href: `/shipments/${r.shipmentId}` }, `#${r.shipmentId}`), ` · ${r.place}`,
        ui.el("span", { class: "sub" }, ui.timeAgo(r.time), r.loggedBy ? ` · by ${r.loggedBy}` : "")),
      ui.badge(r.status)))));

    // Hub map: the same network graph, each place showing how many shipments wait there.
    const waiting = Object.fromEntries(o.hubs.map(h => [h.name, h.waiting]));
    const nodes = net.nodes.map(n => ({ ...n, label: `${n.label} (${waiting[n.label] ?? 0})`, size: 14 + 4 * Math.min(waiting[n.label] ?? 0, 5) }));
    const g = ui.graph(ui.$("#hubmap"), { nodes, edges: net.edges.map(e => ({ ...e, label: "", arrows: "" })) },
      { physics: { solver: "forceAtlas2Based", forceAtlas2Based: { springLength: 170, gravitationalConstant: -70 } } });
    if (g) g.on("click", (p) => {
      if (!p.nodes.length) return;
      const n = nodes.find(x => x.id === p.nodes[0]);
      location.href = `/network?tab=impact&hub=${encodeURIComponent(n.label.replace(/ \(\d+\)$/, ""))}`;
    });

    const c = o.system.counts;
    ui.$("#system").append(ui.el("span", { class: "ok" }, "● Database connected"),
      ...Object.entries(FRIENDLY).map(([key, label]) => ui.el("span", {}, `${label}: ${ui.fmtNum(c[key] ?? 0)}`)));
  } catch (err) {
    ui.message(msg, err.message);
  }
})();
