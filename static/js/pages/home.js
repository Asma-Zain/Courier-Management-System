(async function () {
  const user = await Layout.boot();
  if (!user) return;
  ui.$("#s-ico").append(ui.icon("search"));
  ui.$("#s-go").append(ui.icon("arrow"));
  const err = ui.$("#hero-err");
  ui.$("#hero-search").addEventListener("submit", (e) => {
    e.preventDefault();
    const v = ui.$("#hero-id").value.trim().replace(/^#/, "");
    if (!/^\d+$/.test(v)) { err.textContent = "Enter a shipment ID, for example 10000."; err.hidden = false; return; }
    location.href = `/shipments/${v}`;
  });

  const list = ui.$("#list");
  ui.skeleton(list, 2);
  async function load() {
    try {
      const r = await api.get("/api/shipments", { status: "ACTIVE", pageSize: 3 });
      if (!r.items.length) return ui.emptyState(list, "Nothing in progress", "You have no parcels on the way right now.", { href: "/shipments/new", label: "Send a parcel" });
      ui.clear(list).append(...r.items.map(ui.parcelCard));
    } catch (e) { ui.errorState(list, e.message, load); }
  }
  load();
})();
