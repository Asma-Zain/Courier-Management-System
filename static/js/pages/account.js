(async function () {
  const user = await Layout.boot();
  if (!user) return;
  const msg = ui.$("#msg");
  const staff = user.role === "STAFF";
  const dl = ui.$("#facts");
  const facts = staff
    ? [["Name", `${user.name} ${user.lastName || ""}`], ["Role", user.jobRole || "Staff"], ["Branch", user.branch || ""], ["Email", user.email]]
    : [["Name", `${user.name} ${user.lastName || ""}`], ["Account type", "Customer"], ["Email", user.email]];
  for (const [k, v] of facts) dl.append(ui.el("dt", {}, k), ui.el("dd", {}, v));

  ui.$("#logout").addEventListener("click", async () => { await api.post("/api/auth/logout"); location.href = "/login"; });

  if (!staff) {
    let customer = await api.get(`/api/customers/${user.id}`).catch((e) => { ui.message(msg, e.message); return null; });
    if (!customer) return;
    for (const [k, v] of [["Phone", customer.phone], ["Address", `${customer.street}, ${customer.city}, ${customer.state} ${customer.pincode}`]]) {
      dl.append(ui.el("dt", {}, k), ui.el("dd", {}, v));
    }
    const built = CustomerForm.build(customer, true);
    ui.$("#fields").append(built.grid);
    ui.$("#edit-card").hidden = false;
    ui.$("#edit-card").addEventListener("submit", async (e) => {
      e.preventDefault();
      const box = ui.$("#form-error");
      ui.formError(box, "");
      if (!built.validate()) return;
      const { phone, street, city, state, pincode } = built.read();
      try {
        await api.patch(`/api/customers/${user.id}`, { phone, street, city, state, pincode });
        ui.toast("Your details were updated.");
        setTimeout(() => location.reload(), 700);
      } catch (err) { ui.formError(box, err.message); }
    });
  }
})();
