(async function () {
  const msg = ui.$("#msg");
  const emailInput = ui.$("#email");

  const samples = [
    ["divya@courier.com", "Staff"], ["naveen@courier.com", "Staff"], ["karthik@courier.com", "Staff"],
    ["arun@example.com", "Customer"], ["priya@example.com", "Customer"],
    ["rahul@example.com", "Customer"], ["meera@example.com", "Customer"],
  ];
  const box = ui.$("#samples");
  for (const [email, role] of samples) {
    box.append(ui.el("button", { type: "button", class: "secondary small",
      onclick: () => { emailInput.value = email; ui.$("#login-form").requestSubmit(); } },
      `${email} (${role})`));
  }

  ui.$("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api.post("/api/auth/login", { email: emailInput.value });
      location.href = "/dashboard.html";
    } catch (err) {
      ui.message(msg, err.message);
    }
  });
})();
