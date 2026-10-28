(async function () {
  const user = await Layout.boot();
  if (!user) return;
  const msg = ui.$("#msg");
  const catalogue = await api.get("/api/reports");
  const slug = location.pathname.split("/")[2] || catalogue[0].slug;
  const rep = catalogue.find(r => r.slug === slug);

  // grouped navigation (plain links: choosing a report loads and runs it)
  const nav = ui.$("#report-list");
  for (const group of [...new Set(catalogue.map(r => r.group))]) {
    nav.append(ui.el("li", { class: "group-label" }, group));
    for (const r of catalogue.filter(x => x.group === group)) {
      nav.append(ui.el("li", {}, ui.el("a", { href: `/reports/${r.slug}`, "aria-current": r.slug === slug ? "page" : false }, r.title)));
    }
  }
  if (!rep) { ui.$("#r-title").textContent = "Report not found"; ui.message(msg, "Choose a report from the list."); return; }

  document.title = `${rep.title} · Reports · ${BRAND}`;
  ui.$("#r-title").textContent = rep.title;
  ui.$("#r-desc").textContent = rep.description;
  ui.$("#r-qid").textContent = `Query ${rep.id} (from 04_graph_queries.cypher)`;
  ui.$("#r-cypher").textContent = rep.cypher;
  ui.$("#csv").append(ui.icon("download"), " Export CSV");
  ui.$("#print").append(ui.icon("print"), " Print");
  let rows = [];

  async function run() {
    ui.message(msg, "");
    ui.skeleton(ui.$("#r-table"), 3);
    ui.clear(ui.$("#r-chart"));
    try {
      const params = rep.param ? { customer_id: ui.$("#r-customer").value } : undefined;
      rows = (await api.get(`/api/reports/${slug}`, params)).rows;
      if (rep.chart && rows.length) ui.barChart(ui.$("#r-chart"), rows, rep.chart);
      ui.table(ui.$("#r-table"), rep.columns.map(c => ({ key: c.key, label: c.label, num: ["int", "money", "kg", "hours"].includes(c.format), render: r => ui.cell(c.format, r[c.key]) })),
        rows, { empty: "No rows for this report." });
    } catch (err) { ui.errorState(ui.$("#r-table"), err.message, run); }
  }

  if (rep.param) {
    const customers = await api.get("/api/customers");
    ui.fill(ui.$("#r-customer"), customers.map(c => ({ id: c.customerId, l: `${c.firstName} ${c.lastName}` })), "id", "l");
    ui.$("#r-param").hidden = false;
    ui.$("#r-customer").addEventListener("change", run);
  }
  ui.$("#csv").addEventListener("click", () => rows.length ? ui.csv(`${rep.slug}.csv`, rep.columns, rows) : ui.toast("Nothing to export.", "error"));
  ui.$("#print").addEventListener("click", () => window.print());
  run();
})();
