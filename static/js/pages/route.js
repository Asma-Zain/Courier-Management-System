(async function () {
  const user = await ui.init();
  if (!user) return;
  const msg = ui.$("#msg");

  const [branches, network] = await Promise.all([api.get("/api/branches"), api.get("/api/graph/network")]);
  ui.fill(ui.$("#from"), branches, "name", "name");
  ui.fill(ui.$("#to"), branches, "name", "name");
  if (branches.length > 1) ui.$("#to").selectedIndex = 1;
  const net = ui.graph(ui.$("#graph"), network);

  function highlight(route) {
    if (!net) return;
    const hot = ui.cssVar("--c-accent");
    const nodes = net.body.data.nodes, edges = net.body.data.edges;
    const idOf = (name) => (network.nodes.find(n => n.label === name) || {}).id;
    nodes.update(network.nodes.map(n => ({ id: n.id, borderWidth: route.includes(n.label) ? 4 : 1 })));
    const pairs = route.slice(1).map((n, i) => [idOf(route[i]), idOf(n)]);
    const base = ui.cssVar("--c-border");
    edges.update(edges.get().map((e) => {
      const on = pairs.some(([a, b]) => (e.from === a && e.to === b) || (e.from === b && e.to === a));
      return { id: e.id, width: on ? 4 : 1, color: { color: on ? hot : base } };
    }));
  }

  ui.$("#route-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    ui.message(msg, "");
    const params = { from: ui.$("#from").value, to: ui.$("#to").value };
    try {
      const [hops, kms] = await Promise.all([api.get("/api/routes/fewest-hops", params), api.get("/api/routes/fewest-km", params)]);
      ui.$("#result").hidden = false;
      ui.$("#hops").textContent = hops.route.length
        ? `${hops.route.join(" → ")} · ${hops.hops} hop(s), ${hops.km} km` : "No route between these locations.";
      ui.table(ui.$("#kms"), [
        { key: "route", label: "Route", render: r => r.route.join(" → ") },
        { key: "hops", label: "Hops" }, { key: "km", label: "km" },
      ], kms, "No route between these locations.");
      if (kms.length) highlight(kms[0].route);
    } catch (err) { ui.message(msg, err.message); ui.$("#result").hidden = true; }
  });
})();
