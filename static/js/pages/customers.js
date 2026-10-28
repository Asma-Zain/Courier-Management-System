(async function () {
  const user = await Layout.boot();
  if (!user) return;
  const msg = ui.$("#msg"), list = ui.$("#list"), q = ui.$("#q");
  ui.$("#add").append(ui.icon("plus"), " Add customer");
  let all = [];

  function render() {
    const term = q.value.trim().toLowerCase();
    const rows = all.filter(c => !term || `${c.firstName} ${c.lastName} ${c.email} ${c.phone} ${c.city}`.toLowerCase().includes(term));
    ui.table(list, [
      { key: "customerId", label: "ID" },
      { key: "name", label: "Name", render: c => ui.el("a", { href: `/customers/${c.customerId}` }, `${c.firstName} ${c.lastName}`) },
      { key: "email", label: "Email" }, { key: "phone", label: "Phone" }, { key: "city", label: "City" },
      { key: "shipments", label: "Shipments", num: true, render: c => ui.fmtNum(c.shipments) },
    ], rows, { empty: all.length ? "No customers match your search." : "No customers yet.", href: c => `/customers/${c.customerId}` });
  }
  async function load() {
    ui.skeleton(list, 4);
    try { all = await api.get("/api/customers"); render(); }
    catch (err) { ui.errorState(list, err.message, load); }
  }
  q.addEventListener("input", render);
  ui.$("#add").addEventListener("click", () => CustomerForm.open({ onSaved: load }));
  load();
})();
