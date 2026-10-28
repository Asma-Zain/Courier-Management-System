(async function () {
  const user = await ui.init();
  if (!user) return;
  for (const [id, icon] of [["i-track", "search"], ["i-send", "box"], ["i-route", "route"], ["i-list", "list"]]) {
    ui.$(`#${id}`).append(ui.icon(icon));
  }
  if (user.role === "STAFF") ui.$("#parcels-title").textContent = "All Parcels";

  const { form } = ui.searchBar({ onSubmit: (id) => { location.href = `/track.html?id=${encodeURIComponent(id)}`; } });
  ui.$("#search-slot").append(form);
  ui.tryLine(ui.$("#try"), (id) => `/track.html?id=${id}`);
})();
