"""Layout (no sideways scroll at 375/768/1024/1280), device emulation, dialogs and keyboard behaviour."""
import os
import pathlib

import pytest

from tests.e2e.conftest import BASE, login

pytestmark = pytest.mark.e2e
WIDTHS = [375, 768, 1024, 1280]
STAFF_PAGES = ["/", "/shipments", "/shipments/10000", "/shipments/new", "/network", "/network?tab=impact&hub=Chennai%20Hub",
               "/customers", "/customers/1", "/reports/busiest-locations", "/reports/payments", "/reports/customer-network", "/account"]
CUSTOMER_PAGES = ["/", "/shipments", "/shipments/1", "/shipments/new", "/account", "/customers", "/shipments/2", "/nope"]
SHOTS = os.environ.get("SHOTS_DIR")


def overflow(page):
    return page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")


def check_pages(browser, email, pages, widths, tag):
    for w in widths:
        ctx, page = login(browser, email, viewport={"width": w, "height": 900})
        try:
            for path in pages:
                page.goto(f"{BASE}{path}")
                page.wait_for_load_state("load")
                page.wait_for_timeout(1500)
                scroll, inner = overflow(page)
                assert scroll <= inner, f"{tag} {path} at {w}px scrolls sideways ({scroll} > {inner})"
                if SHOTS:
                    pathlib.Path(SHOTS).mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=f"{SHOTS}/{tag}_{w}_{path.strip('/').replace('/', '_').replace('?', '_') or 'home'}.png", full_page=True)
        finally:
            ctx.close()


def test_staff_pages_never_scroll_sideways(server, browser):
    check_pages(browser, "divya@courier.com", STAFF_PAGES, WIDTHS, "staff")


def test_customer_pages_never_scroll_sideways(server, browser):
    check_pages(browser, "arun@example.com", CUSTOMER_PAGES, WIDTHS, "cust")


@pytest.mark.parametrize("device", ["iPhone 13", "Pixel 7", "iPad (gen 7)"])
def test_device_emulation(server, browser, playwright_instance, device):
    opts = playwright_instance.devices[device]
    for email, pages in (("divya@courier.com", STAFF_PAGES[:8]), ("arun@example.com", CUSTOMER_PAGES[:5])):
        ctx, page = login(browser, email, **{k: v for k, v in opts.items() if k != "default_browser_type"})
        try:
            for path in pages:
                page.goto(f"{BASE}{path}")
                page.wait_for_load_state("load")
                page.wait_for_timeout(1200)
                scroll, inner = overflow(page)
                assert scroll <= inner, f"{device} {email} {path}: {scroll} > {inner}"
                assert page.locator(".site-header .avatar").is_visible()        # account menu never pushed off-screen
                assert page.locator(".head-primary").is_visible()               # primary action stays reachable
                if email.startswith("arun") and path == "/shipments/1":
                    assert not page.locator("#fab").is_visible()                # customers have no staff Actions button
                if SHOTS:
                    pathlib.Path(SHOTS).mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=f"{SHOTS}/{device.split()[0]}_{email[:4]}_{path.strip('/').replace('/', '_').replace('?', '_') or 'home'}.png", full_page=True)
        finally:
            ctx.close()


def test_customer_dialog_stays_open_with_inline_errors(server, browser):
    ctx, page = login(browser, "divya@courier.com")
    try:
        page.goto(f"{BASE}/customers")
        page.wait_for_selector("#add")                                  # appears once the page is ready
        page.click("#add")
        dlg = page.locator("dialog")
        dlg.wait_for()
        dlg.get_by_role("button", name="Create customer").click()          # empty form
        assert dlg.is_visible()
        assert dlg.locator(".field-error").count() >= 8
        assert page.evaluate("document.activeElement.name") == "firstName"   # first invalid field focused
        dlg.locator("input[name=firstName]").fill("Test")
        dlg.locator("input[name=lastName]").fill("Dialog")
        dlg.locator("input[name=email]").fill("nope")
        dlg.locator("input[name=phone]").fill("123")
        dlg.locator("input[name=street]").fill("1 St")
        dlg.locator("input[name=city]").fill("Chennai")
        dlg.locator("input[name=state]").fill("TN")
        dlg.locator("input[name=pincode]").fill("12")
        dlg.get_by_role("button", name="Create customer").click()
        assert dlg.is_visible()
        texts = " ".join(dlg.locator(".field-error").all_inner_texts())
        assert "valid email" in texts and "10 digits" in texts and "6 digits" in texts
        assert page.evaluate("document.activeElement.name") == "email"
        # a duplicate email is a server error and is shown inside the dialog
        dlg.locator("input[name=email]").fill("arun@example.com")
        dlg.locator("input[name=phone]").fill("9876500123")
        dlg.locator("input[name=pincode]").fill("600001")
        dlg.get_by_role("button", name="Create customer").click()
        dlg.locator(".form-error").wait_for()
        assert dlg.is_visible() and "already exists" in dlg.locator(".form-error").inner_text()
        # Escape closes it and focus goes back to the button that opened it
        page.keyboard.press("Escape")
        page.wait_for_selector("dialog", state="detached")
        assert page.evaluate("document.activeElement.id") == "add"
    finally:
        ctx.close()


def test_keyboard_tabs_menu_and_delivered_confirmation(server, browser):
    ctx, page = login(browser, "divya@courier.com")
    try:
        page.goto(f"{BASE}/shipments/10000")
        page.wait_for_selector("#tab-journey")
        page.focus("#tab-journey")
        page.keyboard.press("ArrowRight")
        assert page.get_attribute("#tab-details", "aria-selected") == "true"
        page.keyboard.press("ArrowRight")
        assert page.get_attribute("#tab-graph", "aria-selected") == "true"
        page.keyboard.press("ArrowLeft")
        assert page.get_attribute("#tab-details", "aria-selected") == "true"
        # add-event starts with no status chosen and a disabled button
        page.wait_for_selector("#ev-status")
        assert page.input_value("#ev-status") == ""
        assert page.locator("#ev-submit").is_disabled()
        # account menu: Enter opens, arrows move, Escape closes and returns focus
        page.focus(".user-menu summary")
        page.keyboard.press("Enter")
        page.wait_for_selector(".menu-panel a:focus")
        page.keyboard.press("ArrowDown")
        assert "Log out" in page.evaluate("document.activeElement.textContent")
        page.keyboard.press("Escape")
        assert page.evaluate("document.activeElement.tagName") == "SUMMARY"
    finally:
        ctx.close()


def test_label_prints_on_one_page_with_qr(server, browser):
    import re
    ctx, page = login(browser, "divya@courier.com")
    try:
        page.goto(f"{BASE}/shipments/10000")
        page.wait_for_selector("#print-label")
        page.evaluate("window.print = () => {}")                                  # headless: keep the label on screen
        page.click("#print-label")
        page.wait_for_selector(".print-only img.print-qr", state="attached")
        assert page.get_attribute(".print-only img.print-qr", "src").startswith("data:image/")
        assert page.get_attribute(".print-only img.print-qr", "alt")
        page.emulate_media(media="print")
        assert page.locator(".print-only").is_visible()
        assert not page.locator(".site-header").is_visible()                      # only the label prints
        assert "10000" in page.locator(".print-only").inner_text()
        pdf = page.pdf()
        assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 1                  # one page
    finally:
        ctx.close()


def reach_review_step(page, sender="1", receiver="priya@example.com", weight="2"):
    page.goto(f"{BASE}/shipments/new")
    page.wait_for_selector("select")
    page.select_option("select >> nth=0", value=sender)
    page.fill("input[type=email]", receiver)
    page.wait_for_selector(".chip-ok")
    page.click("text=Next: packages")
    card = page.locator(".package-card").first
    card.locator("input").nth(0).fill("Books")
    card.locator("input").nth(1).fill("30x20x10 cm")
    card.locator("input").nth(2).fill(weight)


def test_booking_form_edge_cases(server, browser):
    ctx, page = login(browser, "divya@courier.com", viewport={"width": 1280, "height": 720})
    try:
        # staff cannot book a parcel from Arun to Arun: stopped on step 1, nothing is created
        page.goto(f"{BASE}/shipments/new")
        page.wait_for_selector("select")
        page.select_option("select >> nth=0", value="1")
        page.fill("input[type=email]", "arun@example.com")
        page.wait_for_selector(".chip-ok")
        page.click("text=Next: packages")
        assert "must be different" in page.locator(".field-error").inner_text()
        assert page.locator(".package-card").count() == 0

        # a negative weight never shows up in the total
        reach_review_step(page, weight="-5")
        assert "-5" not in page.locator(".total-line").inner_text()
        assert "0 kg" in page.locator(".total-line").inner_text()
        page.click("text=Next: review")
        assert "at least 0.01" in page.locator(".field-error").inner_text()

        # ticking "record the payment" keeps the Book button on screen
        page.locator(".package-card").first.locator("input").nth(2).fill("2")
        page.click("text=Next: review")
        page.get_by_label("Record the payment now").check()
        box = page.get_by_role("button", name="Book shipment").bounding_box()
        assert box and box["y"] + box["height"] <= 720, box
    finally:
        ctx.close()


def test_add_event_without_status_explains_itself(server, browser):
    ctx, page = login(browser, "divya@courier.com")
    try:
        page.goto(f"{BASE}/shipments/10000")
        page.wait_for_selector("#ev-status")
        assert page.input_value("#ev-status") == ""
        page.click("#ev-submit")                                                   # nothing chosen
        assert "Choose the next status" in page.locator("#actions .field-error").inner_text()
        assert page.evaluate("document.activeElement.id") == "ev-status"
    finally:
        ctx.close()


def test_healthz_is_reachable_from_page_javascript(server, browser):
    ctx, page = login(browser, "divya@courier.com")
    try:
        results = page.evaluate("Promise.all([fetch('/healthz'), fetch('/readyz')].map(p => p.then(r => r.status)))")
        assert results == [200, 200]
        for _ in range(5):   # repeat: it should never intermittently fail
            assert page.evaluate("fetch('/healthz').then(r => r.status)") == 200
    finally:
        ctx.close()
