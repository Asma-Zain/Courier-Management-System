/* Customer fields + validation, shared by the add/edit modal and the account page. */
const CustomerForm = {
  RULES: {
    firstName: (v) => v ? null : "Enter a first name.",
    lastName: (v) => v ? null : "Enter a last name.",
    email: (v) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v) ? null : "Enter a valid email address.",
    phone: (v) => /^\d{10}$/.test(v) ? null : "Phone must be exactly 10 digits.",
    street: (v) => v ? null : "Enter a street address.",
    city: (v) => v ? null : "Enter a city.",
    state: (v) => v ? null : "Enter a state.",
    pincode: (v) => /^\d{6}$/.test(v) ? null : "Pincode must be exactly 6 digits.",
  },
  LABELS: { firstName: "First name", lastName: "Last name", email: "Email", phone: "Phone (10 digits)", street: "Street",
            city: "City", state: "State", pincode: "Pincode (6 digits)" },

  /* values: existing customer or {}; editing: only phone and address may change */
  build(values = {}, editing = false) {
    const controls = {};
    const grid = ui.el("div", { class: "form-grid" });
    for (const key of Object.keys(CustomerForm.LABELS)) {
      const locked = editing && ["firstName", "lastName", "email"].includes(key);
      const input = ui.el("input", { name: key, value: values[key] ?? "", disabled: locked,
        type: key === "email" ? "email" : "text", inputmode: ["phone", "pincode"].includes(key) ? "numeric" : null,
        autocomplete: "off" });
      controls[key] = input;
      grid.append(ui.field(CustomerForm.LABELS[key], input, { required: !locked }));
    }
    return {
      grid, controls,
      validate: () => ui.check(Object.entries(controls).filter(([, c]) => !c.disabled).map(([k, c]) => [c, CustomerForm.RULES[k]])),
      read: () => Object.fromEntries(Object.entries(controls).map(([k, c]) => [k, c.value.trim()])),
    };
  },

  /* Modal for adding (no customer) or editing a customer. */
  open({ customer = null, email = "", onSaved }) {
    const form = ui.el("form", { id: "customer-form", novalidate: true });
    const built = CustomerForm.build(customer || { email }, !!customer);
    const errBox = ui.el("div", { class: "form-error", role: "alert", hidden: true });
    form.append(built.grid, errBox);
    if (customer) form.prepend(ui.el("p", { class: "hint" }, "Only phone and address can be changed."));
    const dlg = ui.dialog({
      title: customer ? `Edit ${customer.firstName} ${customer.lastName}` : "Add customer", body: form,
      actions: [{ label: "Cancel", kind: "secondary" }, { label: customer ? "Save changes" : "Create customer", submit: true, form: "customer-form" }],
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      ui.formError(errBox, "");
      if (!built.validate()) return;
      const data = built.read();
      try {
        let saved;
        if (customer) {
          const { phone, street, city, state, pincode } = data;
          saved = await api.patch(`/api/customers/${customer.customerId}`, { phone, street, city, state, pincode });
        } else {
          saved = await api.post("/api/customers", data);
        }
        dlg.close();
        ui.toast(customer ? "Customer updated." : `Customer ${saved.customerId} created.`);
        if (onSaved) onSaved(saved);
      } catch (err) { ui.formError(errBox, err.message); }
    });
    return dlg;
  },
};
