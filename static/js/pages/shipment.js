(async function () {
  const user = await Layout.boot();
  if (!user) return;
  const staff = user.role === "STAFF";
  const id = parseInt(location.pathname.split("/").pop(), 10);
  const msg = ui.$("#msg");
  let ship = null, graphNet = null, tabApi = null;

  ui.$("#back").prepend(ui.icon("back"));
  ui.$("#back").lastChild.textContent = staff ? " Back to shipments" : " Back to my parcels";
  ui.$("#copy-link").append(ui.icon("copy"));
  ui.$("#share").append(ui.icon("share"));
  ui.$("#print-label").append(ui.icon("print"), " Print label");
  ui.skeleton(ui.$("#skeleton"), 3);

  async function load() {
    const [s, journey, graph] = await Promise.all([
      api.get(`/api/shipments/${id}`), api.get(`/api/shipments/${id}/track`), api.get(`/api/graph/shipment/${id}`)]);
    ship = s;
    document.title = `Shipment #${id} · ${BRAND}`;
    ui.$("#d-id").textContent = `#${s.shipmentId}`;
    ui.clear(ui.$("#d-route")).append(s.sender.city, ui.icon("arrow"), s.receiver.city);
    ui.$("#d-sub").textContent = `${s.shipmentType[0] + s.shipmentType.slice(1).toLowerCase()} · Booked ${ui.fmtDay(s.bookingDate)} at ${s.bookedAt}`;
    ui.clear(ui.$("#d-status")).append(ui.badge(s.status));
    ui.clear(ui.$("#d-pay")).append(ui.payBadge(s.paymentState));

    ui.timeline(ui.$("#timeline"), journey, s.status, { bookingDate: s.bookingDate, bookedAt: s.bookedAt });
    ui.routeMap(ui.$("#map"), ui.mapData(s, journey));
    const eta = ui.clear(ui.$("#eta"));
    if (s.place) eta.append(ui.el("strong", {}, s.status === "DELIVERED" ? `Delivered at ${s.place}` : `Last scan: ${s.place}`),
      ui.el("span", { class: "muted small" }, ui.timeAgo(s.since)));

    const dl = ui.clear(ui.$("#details"));
    const rows = [
      ["Sender", `${s.sender.firstName} ${s.sender.lastName} · ${s.sender.city}`],
      ["Receiver", `${s.receiver.firstName} ${s.receiver.lastName} · ${s.receiver.city}`],
      ["Weight", `${s.weightKg} kg`], ["Amount", ui.fmtMoney(s.totalAmount)],
      ["Paid", ui.fmtMoney(s.paidAmount)], ["Outstanding", ui.fmtMoney(s.outstanding)],
      ["Payment", s.payment ? `${ui.fmtMoney(s.payment.amount)} by ${s.payment.mode} · ${s.payment.status === "PAID" ? "Paid" : "Pending"} (${ui.fmtDay(s.payment.paymentDate)})` : "No payment recorded"],
    ];
    if (staff) { rows.splice(2, 0, ["Sender phone", s.sender.phone], ["Receiver phone", s.receiver.phone]); }
    for (const [k, v] of rows) dl.append(ui.el("dt", {}, k), ui.el("dd", {}, v));
    ui.table(ui.$("#packages"), [
      { key: "description", label: "Description" }, { key: "packageType", label: "Type" },
      { key: "dimensions", label: "Dimensions" }, { key: "weightKg", label: "Weight", num: true, render: r => `${r.weightKg} kg` },
    ], s.packages, { empty: "No packages." });

    ui.$("#skeleton").hidden = true;
    ui.$("#result").hidden = false;
    renderGraph(graph);
    if (staff) await loadActions();
  }

  function renderGraph(graph) {
    ui.$("#graph")._data = graph;                       // drawn when the Graph tab opens (needs a visible canvas)
    if (graphNet) { graphNet.destroy(); graphNet = null; }
    if (!ui.$("#panel-graph").hidden) drawGraph();
  }
  function drawGraph() {
    const g = ui.$("#graph")._data;
    if (!g || graphNet) return;
    // relationship names go in the tooltip so lines stay uncluttered and labels never overlap
    graphNet = ui.graph(ui.$("#graph"), { nodes: g.nodes, edges: g.edges.map(e => ({ ...e, title: e.label, label: "" })) },
      { layout: { hierarchical: { direction: "LR", sortMethod: "directed", levelSeparation: 170, nodeSpacing: 120 } }, physics: false });
  }

  tabApi = ui.tabs(ui.$("#tabs"), [{ id: "journey", label: "Journey" }, { id: "details", label: "Details" }, { id: "graph", label: "Graph" }],
    (tab) => { if (tab === "graph") setTimeout(drawGraph, 0); }, "journey");

  // ---------------- staff actions ----------------
  const evStatus = ui.$("#ev-status"), evBranch = ui.$("#ev-branch");
  let nextInfo = null, branches = [];

  function fillBranches() {
    const delivering = evStatus.value === "DELIVERED" && nextInfo.deliveryPlaces.length;
    const names = delivering ? nextInfo.deliveryPlaces : branches.map(b => b.name);
    ui.fill(evBranch, names.map(n => ({ n })), "n", "n");
    evBranch.value = names.includes(nextInfo.currentPlace) ? nextInfo.currentPlace : names[0];
    ui.$("#ev-hint").textContent = delivering ? `Delivery is recorded in the receiver’s city (${ship.receiver.city}).` : "";
  }

  async function loadActions() {
    ui.$("#actions").hidden = false;
    ui.$("#fab").hidden = false;
    [nextInfo, branches] = await Promise.all([api.get(`/api/shipments/${id}/next-statuses`), branches.length ? branches : api.get("/api/branches")]);
    const none = !nextInfo.allowed.length;
    ui.$("#event-form").classList.toggle("muted", none);
    ui.$("#ev-submit").disabled = none;
    evStatus.disabled = evBranch.disabled = ui.$("#ev-note").disabled = none;
    if (none) {
      ui.fill(evStatus, [{ s: "", l: `Final (${ui.statusLabel(nextInfo.current)})` }], "s", "l");
      ui.fill(evBranch, [], "n", "n");
      ui.$("#ev-hint").textContent = "This shipment is finished, so no more events can be added.";
    } else {
      ui.fill(evStatus, nextInfo.allowed.map(s => ({ s, l: ui.statusLabel(s) })), "s", "l");
      fillBranches();
    }
    const payForm = ui.$("#pay-form"), done = ui.$("#pay-done");
    const canPay = !ship.payment && ship.status !== "CANCELLED";
    payForm.hidden = !canPay;
    done.hidden = canPay;
    done.textContent = ship.payment ? "A payment is already recorded for this shipment." : "Cancelled shipments take no payment.";
    ui.$("#pay-amount").value = ship.outstanding;
  }
  evStatus.addEventListener("change", () => nextInfo && fillBranches());
  for (const m of ["UPI", "CARD", "NETBANKING", "CASH"]) ui.$("#pay-mode").append(ui.el("option", { value: m }, m));
  for (const [v, l] of [["PAID", "Paid"], ["PENDING", "Pending"]]) ui.$("#pay-status").append(ui.el("option", { value: v }, l));

  ui.$("#event-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const box = ui.$("#ev-error");
    ui.formError(box, "");
    try {
      const r = await api.post(`/api/shipments/${id}/events`, { status: evStatus.value, branch: evBranch.value, note: ui.$("#ev-note").value.trim() || null });
      ui.$("#ev-note").value = "";
      await load();
      ui.toast(`Added: ${ui.statusLabel(r.status)} at ${r.place}.`);
    } catch (err) { ui.formError(box, err.message); }
  });
  ui.$("#pay-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const box = ui.$("#pay-error"), amount = ui.$("#pay-amount");
    ui.formError(box, "");
    if (!ui.check([[amount, (v) => !(parseFloat(v) > 0) ? "Enter an amount above 0." : (parseFloat(v) > ship.outstanding ? `Cannot exceed the outstanding ${ui.fmtMoney(ship.outstanding)}.` : null)]])) return;
    try {
      await api.post(`/api/shipments/${id}/payment`, { amount: parseFloat(amount.value), mode: ui.$("#pay-mode").value, status: ui.$("#pay-status").value });
      await load();
      ui.toast("Payment recorded.");
    } catch (err) { ui.formError(box, err.message); }
  });

  ui.$("#fab").addEventListener("click", () => ui.$("#actions").classList.toggle("open"));
  ui.$("#copy-link").addEventListener("click", () => ui.copy(location.href));
  ui.$("#share").addEventListener("click", async () => {
    if (navigator.share) { try { await navigator.share({ title: `Shipment #${id}`, url: location.href }); } catch (e) { /* cancelled */ } }
    else ui.copy(location.href);
  });

  ui.$("#print-label").addEventListener("click", () => {
    ui.$$(".print-only").forEach(n => n.remove());
    const label = ui.el("div", { class: "print-only" },
      ui.el("h1", {}, `Parcelly · Shipment #${ship.shipmentId}`),
      ui.el("p", {}, ui.el("strong", {}, "To: "), `${ship.receiver.firstName} ${ship.receiver.lastName}, ${ship.receiver.city} · ${ship.receiver.phone}`),
      ui.el("p", {}, ui.el("strong", {}, "From: "), `${ship.sender.firstName} ${ship.sender.lastName}, ${ship.sender.city}`),
      ui.el("p", {}, `${ship.shipmentType} · ${ship.weightKg} kg · ${ship.packages.length} package(s)`),
      ui.el("p", {}, `Booked ${ui.fmtDay(ship.bookingDate)} at ${ship.bookedAt}`));
    document.body.append(label);
    document.body.classList.add("printing-label");
    window.print();
  });
  window.addEventListener("afterprint", () => { document.body.classList.remove("printing-label"); ui.$$(".print-only").forEach(n => n.remove()); });

  try { await load(); }
  catch (err) { ui.$("#skeleton").hidden = true; ui.message(msg, err.message); }
})();
