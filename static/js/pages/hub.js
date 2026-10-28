(async function () {
  const user = await ui.init({ staffOnly: true });
  if (!user) return;
  const msg = ui.$("#msg");
  const branches = await api.get("/api/branches");
  ui.fill(ui.$("#hub"), branches, "name", "name");
  const preferred = branches.findIndex(b => b.name === "Chennai Hub");
  if (preferred >= 0) ui.$("#hub").selectedIndex = preferred;

  async function run() {
    ui.message(msg, "");
    try {
      const rows = await api.get(`/api/hubs/${encodeURIComponent(ui.$("#hub").value)}/impact`);
      ui.table(ui.$("#result"), [
        { key: "shipment", label: "Shipment", render: r => ui.el("a", { href: `/track.html?id=${r.shipment}` }, String(r.shipment)) },
        { key: "status", label: "Status", render: r => ui.badge(r.status) },
        { key: "receiver", label: "Receiver waiting" }, { key: "phone", label: "Phone" },
      ], rows, "No shipments are currently at this location.");
    } catch (err) { ui.message(msg, err.message); }
  }
  ui.$("#hub-form").addEventListener("submit", (e) => { e.preventDefault(); run(); });
  run();
})();
