(async function () {
  const user = await ui.init();
  if (!user) return;
  const msg = ui.$("#msg");
  ui.$("#back").append(ui.icon("back"));
  const id = ui.qs("id");
  if (!id) { ui.message(msg, "Open a shipment from the Track page to see it on the map."); return; }
  ui.$("#back").href = `/track.html?id=${encodeURIComponent(id)}`;
  ui.$("#view-all").href = `/track.html?id=${encodeURIComponent(id)}`;
  try {
    const [ship, journey] = await Promise.all([api.get(`/api/shipments/${id}`), api.get(`/api/shipments/${id}/track`)]);
    ui.routeMap(ui.$("#map"), ui.mapData(ship, journey));
    ui.etaCard(ui.$("#eta"), ship);
    ui.$("#d-id").textContent = `#${ship.shipmentId}`;
    ui.clear(ui.$("#d-status")).append(ui.badge(ship.status || "BOOKED"));
    ui.$("#d-from").textContent = ship.sender.city;
    ui.$("#d-to").textContent = ship.receiver.city;
    ui.$("#d-scan").textContent = ship.place || "No scans yet";
    ui.$("#d-when").textContent = ship.since ? ui.fmtTime(ship.since) : "";
    ui.$("#result").hidden = false;
  } catch (err) { ui.message(msg, err.message); }
})();
