(async function () {
  const user = await ui.init();
  if (!user) return;
  const msg = ui.$("#msg");

  const shipCols = [
    { key: "shipmentId", label: "Id", render: r => ui.el("a", { href: `/track.html?id=${r.shipmentId}` }, String(r.shipmentId)) },
    { key: "bookingDate", label: "Booked" },
    { key: "shipmentType", label: "Type" },
    { key: "sender", label: "Sender" },
    { key: "receiver", label: "Receiver" },
    { key: "weightKg", label: "Kg" },
    { key: "totalAmount", label: "Amount" },
    { key: "status", label: "Status", render: r => ui.badge(r.status) },
    { key: "place", label: "Now at" },
  ];

  try {
    if (user.role === "STAFF") {
      ui.$("#staff-only").hidden = false;
      ui.$("#ship-title").textContent = "All shipments";
      const [dash, board] = await Promise.all([api.get("/api/dashboard"), api.get("/api/shipments/status")]);
      const counts = ui.$("#counts");
      for (const c of dash.counts) {
        counts.append(ui.el("div", { class: "stat" }, ui.el("span", { class: "num" }, String(c.nodes)), ui.el("span", { class: "lbl" }, c.label)));
      }
      ui.table(ui.$("#statuses"), [
        { key: "status", label: "Status", render: r => ui.badge(r.status) },
        { key: "shipments", label: "Shipments" },
      ], dash.statuses);
      ui.$("#outstanding-total").textContent = `Total outstanding: ${dash.outstanding.total}`;
      ui.table(ui.$("#outstanding"), [
        { key: "shipment", label: "Shipment" }, { key: "outstanding", label: "Outstanding" },
      ], dash.outstanding.shipments, "Everything is paid.");
      ui.table(ui.$("#board"), [
        { key: "shipment", label: "Shipment", render: r => ui.el("a", { href: `/track.html?id=${r.shipment}` }, String(r.shipment)) },
        { key: "status", label: "Status", render: r => ui.badge(r.status) },
        { key: "place", label: "Place" },
        { key: "since", label: "Since", render: r => ui.fmtTime(r.since) },
      ], board);
    } else {
      ui.$("#customer-only").hidden = false;
      ui.$("#ship-title").textContent = "My shipments (sent or received)";
      const me = await api.get(`/api/customers/${user.id}`);
      const dl = ui.$("#profile");
      for (const [k, v] of [["Name", `${me.firstName} ${me.lastName}`], ["Email", me.email], ["Phone", me.phone],
                            ["Address", `${me.street}, ${me.city}, ${me.state} ${me.pincode}`]]) {
        dl.append(ui.el("dt", {}, k), ui.el("dd", {}, v));
      }
    }
    ui.table(ui.$("#shipments"), shipCols, await api.get("/api/shipments"), "No shipments yet.");
  } catch (err) {
    ui.message(msg, err.message);
  }
})();
