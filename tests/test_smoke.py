"""End-to-end smoke test: serves docs/ exactly as GitHub Pages does and drives the real app.

Run:  pip install pytest playwright && python -m playwright install chromium && python -m pytest -q
"""
import functools
import http.server
import pathlib
import threading

import pytest
from playwright.sync_api import sync_playwright

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"


@pytest.fixture(scope="module")
def base_url():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


@pytest.fixture()
def page(base_url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={"width": 1280, "height": 860})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
        pg.goto(base_url)
        yield pg
        browser.close()
        assert not errors, f"browser errors: {errors}"


def setup_week(page):
    for day in ["Sun", "Mon", "Tue", "Wed", "Thu"]:
        page.get_by_role("button", name=day, exact=True).first.click()
    page.get_by_role("button", name="Continue").click()


def add_course(page, code, name, day_index, start, room):
    page.get_by_role("button", name="+ Add your first course").click()
    page.get_by_placeholder("MATH 103").fill(code)
    page.get_by_placeholder("Calculus for Computational Science").fill(name)
    page.get_by_role("button", name="+ Add a time").click()
    page.select_option("#sDay", index=day_index)
    page.fill("#sStart", start)
    page.get_by_placeholder("G006-B").fill(room)
    page.get_by_role("button", name="Save time").click()
    page.get_by_role("button", name="Save", exact=True).click()


def test_onboarding_asks_for_teaching_days(page):
    assert "Which days do you have classes?" in page.inner_text("body")
    setup_week(page)
    assert "No courses yet" in page.inner_text("body")


def test_course_is_saved_locally_and_shown_in_week_view_after_reload(page):
    setup_week(page)
    add_course(page, "CSAI 205", "Circuits and Electronics", 1, "10:00", "Room C201")
    page.reload()
    stored = page.evaluate("localStorage.getItem('spine.courses')")
    assert "CSAI 205" in stored
    page.locator("button", has_text="Week").first.click(force=True)
    body = page.inner_text("body")
    assert "CSAI 205" in body and "C201" in body


def test_service_worker_registers_for_offline_use(page):
    page.wait_for_function("navigator.serviceWorker.getRegistrations().then(r => r.length > 0)")
    assert page.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)") == 1


def test_manifest_is_linked_and_valid(page, base_url):
    href = page.get_attribute("link[rel=manifest]", "href")
    manifest = page.request.get(base_url + href).json()
    assert manifest["name"] and manifest["start_url"] and manifest["icons"]
    assert manifest["display"] in ("standalone", "fullscreen", "minimal-ui")
