(async function () {
  const user = await ui.init();
  if (!user) return;
  const msg = ui.$("#msg");
  const id = ui.qs("id");
  if (!id) { ui.message(msg, "Open a delivered shipment from the Track page."); return; }
  try {
    const ship = await api.get(`/api/shipments/${id}`);
    if (ship.status !== "DELIVERED") {
      ui.message(msg, `Shipment #${ship.shipmentId} is not delivered yet (${ui.label(ship.status || "BOOKED")}).`);
      ui.$("#msg").append(" ", ui.el("a", { href: `/track.html?id=${ship.shipmentId}` }, "Track it"));
      return;
    }
    ui.$("#d-id").textContent = `#${ship.shipmentId}`;
    ui.$("#d-when").textContent = ui.fmtTime(ship.since);
    ui.$("#d-who").textContent = `${ship.receiver.firstName} ${ship.receiver.lastName}`;
    ui.$("#details").href = `/track.html?id=${ship.shipmentId}`;
    ui.$("#result").hidden = false;
  } catch (err) { ui.message(msg, err.message); }
})();
