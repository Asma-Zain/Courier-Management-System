"""Browser smoke test (Playwright driving the installed Google Chrome). Needs Aura credentials.
Run: make e2e. Uses customers 9001/9002 and removes everything it created."""
import re

import pytest

from tests.e2e.conftest import BASE, login  # noqa: E402

pytestmark = pytest.mark.e2e


def test_staff_flow_and_customer_scope(server, browser):
    ctx, page = login(browser, "divya@courier.com")
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    try:
        page.wait_for_selector(".site-nav a")
        assert page.locator(".site-nav a").count() == 5
        assert page.locator("h1").inner_text() == "Overview"

        for cid in (9001, 9002):
            r = page.request.post(f"{BASE}/api/customers", data={
                "customerId": cid, "firstName": "Test", "lastName": f"User{cid}", "email": f"t{cid}@example.com",
                "phone": "9000000099", "street": "1 Test Street", "city": "Madurai", "state": "Tamil Nadu", "pincode": "625001"})
            assert r.status == 201, r.text()

        # book with two packages through the 3-step flow
        page.goto(f"{BASE}/shipments/new")
        page.wait_for_selector("select")
        page.select_option("select >> nth=0", value="9001")
        page.fill("input[type=email]", "t9002@example.com")
        page.wait_for_selector(".chip-ok")
        page.click("text=Next: packages")
        page.click("text=Add another package")
        cards = page.locator(".package-card")
        assert cards.count() == 2
        for i, (desc, kg) in enumerate([("Gift box", "2"), ("Cards", "1.5")]):
            card = cards.nth(i)
            card.locator("input").nth(0).fill(desc)
            card.locator("input").nth(1).fill("30x20x10 cm")
            card.locator("input").nth(2).fill(kg)
        page.click("text=Next: review")
        assert "₹170" in page.locator(".price").inner_text()
        page.click("text=Book shipment")
        page.wait_for_selector(".success")
        sid = int(re.search(r"Shipment #(\d+)", page.locator(".success p").inner_text()).group(1))

        # drive it to Delivered; only valid next statuses are offered
        page.click("text=Track it")
        page.wait_for_selector("#actions")
        for status in ("PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"):
            options = page.locator("#ev-status option").all_inner_texts()
            assert ("Delivered" in options) == (status == "DELIVERED"), options
            page.select_option("#ev-status", value=status)
            page.click("#ev-submit")
            if status == "DELIVERED":                       # final status: the app asks first
                page.get_by_role("button", name="Mark delivered").click()
            page.wait_for_selector(f".toast:has-text('{status.replace('_', ' ').capitalize()}')")
        assert page.locator("#ev-submit").is_disabled()

        # record payment (amount pre-filled with the outstanding balance)
        assert page.input_value("#pay-amount") == "170"
        page.click("#pay-form button[type=submit]")
        page.wait_for_selector("#d-pay .badge.PAID")

        page.goto(f"{BASE}/shipments?q={sid}")
        row = page.locator("tbody tr", has_text=f"#{sid}")
        row.wait_for()
        assert "Delivered" in row.inner_text() and "Paid" in row.inner_text()
        assert not [e for e in errors if "403" not in e]
    finally:
        ctx.close()

    # customer: own parcels only; staff pages give a 403 page
    ctx, page = login(browser, "arun@example.com")
    try:
        page.wait_for_selector(".site-nav a")
        assert page.locator(".site-nav a").count() == 2
        page.goto(f"{BASE}/shipments")
        page.wait_for_selector(".parcel-card")
        assert sorted(page.locator(".parcel-card .id").all_inner_texts()) == ["#1", "#10000", "#4"]
        assert page.goto(f"{BASE}/customers").status == 403
        assert "staff only" in page.content().lower()
        assert page.goto(f"{BASE}/shipments/2").status == 403
        assert page.goto(f"{BASE}/network").status == 403
        assert page.goto(f"{BASE}/nope").status == 404
    finally:
        ctx.close()
