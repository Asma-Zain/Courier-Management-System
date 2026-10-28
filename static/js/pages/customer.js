(async function () {
  const user = await Layout.boot();
  if (!user) return;
  const id = parseInt(location.pathname.split("/").pop(), 10);
  const msg = ui.$("#msg");
  let customer = null;

  async function load() {
    try {
      customer = await api.get(`/api/customers/${id}`);
      document.title = `${customer.firstName} ${customer.lastName} · ${BRAND}`;
      ui.$("#name").textContent = `${customer.firstName} ${customer.lastName}`;
      const dl = ui.clear(ui.$("#facts"));
      for (const [k, v] of [["Customer ID", customer.customerId], ["Email", customer.email], ["Phone", customer.phone],
          ["Address", `${customer.street}, ${customer.city}, ${customer.state} ${customer.pincode}`], ["Shipments", customer.shipments]]) {
        dl.append(ui.el("dt", {}, k), ui.el("dd", {}, String(v)));
      }
      ui.$("#result").hidden = false;
      const box = ui.$("#shipments");
      ui.skeleton(box, 2);
      const r = await api.get("/api/shipments", { customerId: id, pageSize: 100 });
      ui.table(box, ui.shipmentColumns(), r.items, { empty: "This customer has no shipments.", href: row => `/shipments/${row.shipmentId}` });
    } catch (err) { ui.message(msg, err.status === 404 ? "This customer does not exist." : err.message); }
  }

  ui.$("#edit").addEventListener("click", () => CustomerForm.open({ customer, onSaved: load }));
  ui.$("#delete").addEventListener("click", async () => {
    const ok = await ui.confirm({ title: `Delete ${customer.firstName} ${customer.lastName}?`,
      message: "This permanently removes the customer. It cannot be undone. Customers who have sent or received shipments cannot be deleted.",
      confirmLabel: "Delete customer", danger: true });
    if (!ok) return;
    try { await api.del(`/api/customers/${id}`); location.href = "/customers"; }
    catch (err) { ui.message(msg, err.message); msg.scrollIntoView({ block: "center" }); msg.setAttribute("tabindex", "-1"); msg.focus(); }
  });
  load();
})();
