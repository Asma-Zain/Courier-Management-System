(async function () {
  const user = await ui.init();
  if (!user) return;
  const staff = user.role === "STAFF";
  const msg = ui.$("#msg"), list = ui.$("#list");
  ui.$("#title").textContent = staff ? "All Parcels" : "My Parcels";
  ui.$("#head-action").prepend(ui.icon("search"));
  if (!staff) ui.$("#head-actions").append(ui.el("a", { class: "button secondary", href: "/book.html" }, "Send a Parcel"));

  const tabs = [
    ["active", "Active", s => s.status !== "DELIVERED" && s.status !== "CANCELLED"],
    ["delivered", "Delivered", s => s.status === "DELIVERED"],
    ["cancelled", "Cancelled", s => s.status === "CANCELLED"],
  ];
  let all = [], current = "active";

  function render() {
    const filter = tabs.find(t => t[0] === current)[2];
    const rows = all.filter(filter);
    ui.clear(list);
    if (!rows.length) {
      ui.emptyState(list, "Nothing here just yet.",
        all.length ? "No parcels in this tab." : (staff ? "No shipments have been booked." : "You have no parcels yet."),
        { href: "/track.html", label: "Track a Parcel" });
      return;
    }
    list.append(...rows.map(ui.parcelCard));
  }

  function drawTabs() {
    ui.clear(ui.$("#tabs")).append(...tabs.map(([key, label, f]) =>
      ui.el("button", { class: "tab", type: "button", role: "tab", "aria-selected": String(key === current),
        onclick: () => { current = key; drawTabs(); render(); } }, `${label} (${all.filter(f).length})`)));
  }

  ui.skeleton(list, 3);
  try {
    all = await api.get("/api/shipments");
    drawTabs();
    render();
  } catch (err) {
    ui.clear(list);
    ui.message(msg, err.message);
  }
})();
