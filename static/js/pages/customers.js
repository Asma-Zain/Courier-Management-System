(async function () {
  const user = await ui.init({ staffOnly: true });
  if (!user) return;
  const msg = ui.$("#msg");
  const form = ui.$("#cust-form");
  const fields = ["firstName", "lastName", "email", "phone", "street", "city", "state", "pincode"];
  const readonlyWhenEditing = ["firstName", "lastName", "email"];
  let editing = null;

  function setMode(customer) {
    editing = customer ? customer.customerId : null;
    ui.$("#form-title").textContent = customer ? `Edit customer ${customer.customerId}` : "Add customer";
    ui.$("#save").textContent = customer ? "Save changes" : "Create customer";
    ui.$("#cancel").hidden = !customer;
    ui.$("#edit-hint").hidden = !customer;
    for (const f of fields) {
      ui.$(`#${f}`).value = customer ? customer[f] : "";
      ui.$(`#${f}`).disabled = !!customer && readonlyWhenEditing.includes(f);
    }
    if (customer) form.scrollIntoView({ behavior: "smooth" });
  }

  async function refresh() {
    ui.table(ui.$("#list"), [
      { key: "customerId", label: "Id" },
      { key: "name", label: "Name", render: c => `${c.firstName} ${c.lastName}` },
      { key: "email", label: "Email" }, { key: "phone", label: "Phone" },
      { key: "city", label: "City" }, { key: "state", label: "State" }, { key: "pincode", label: "Pincode" },
      { key: "actions", label: "", render: c => ui.el("span", {},
          ui.el("button", { class: "link", type: "button", onclick: () => setMode(c) }, "Edit"),
          ui.el("button", { class: "link", type: "button", onclick: () => remove(c) }, "Delete")) },
    ], await api.get("/api/customers"));
  }

  async function remove(c) {
    if (!confirm(`Delete ${c.firstName} ${c.lastName}?`)) return;
    ui.message(msg, "");
    try { await api.del(`/api/customers/${c.customerId}`); ui.message(msg, "Customer deleted.", "ok"); await refresh(); }
    catch (err) { ui.message(msg, err.message); }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    ui.message(msg, "");
    try {
      if (editing) {
        await api.patch(`/api/customers/${editing}`, {
          phone: ui.$("#phone").value, street: ui.$("#street").value, city: ui.$("#city").value,
          state: ui.$("#state").value, pincode: ui.$("#pincode").value });
        ui.message(msg, "Customer updated.", "ok");
      } else {
        const body = {};
        for (const f of fields) body[f] = ui.$(`#${f}`).value;
        const c = await api.post("/api/customers", body);
        ui.message(msg, `Customer ${c.customerId} created.`, "ok");
      }
      setMode(null);
      await refresh();
    } catch (err) { ui.message(msg, err.message); }
  });
  ui.$("#cancel").addEventListener("click", () => setMode(null));

  setMode(null);
  refresh().catch(err => ui.message(msg, err.message));
})();
