"""Static contract of the extension, readable without a browser.

This file exists because of a real bug: `popup.js` bound handlers to seven sign-in
elements that were never added to `popup.html`. `bindEvents()` threw on the first
`addEventListener`, so no other handler was attached and the analysis never ran — the
extension was dead on open, and nothing in the test suite could see it.
"""

import json
import re
from pathlib import Path

EXTENSION = Path(__file__).resolve().parents[2] / "extension"
POPUP_JS = (EXTENSION / "popup" / "popup.js").read_text()
POPUP_HTML = (EXTENSION / "popup" / "popup.html").read_text()
POPUP_CSS = (EXTENSION / "popup" / "popup.css").read_text()
MANIFEST = json.loads((EXTENSION / "manifest.json").read_text())

# API -> permission that must be declared in the manifest for the call to work at all.
REQUIRED_PERMISSIONS = {
    "chrome.storage": "storage",
    "chrome.scripting": "scripting",
    "chrome.alarms": "alarms",
}


def js_files():
    return sorted(EXTENSION.rglob("*.js"))


class TestPopupMarkup:
    def test_every_element_referenced_exists(self):
        referenced = set(re.findall(r"getElementById\(['\"]([A-Za-z0-9_-]+)['\"]\)", POPUP_JS))
        present = set(re.findall(r'id="([A-Za-z0-9_-]+)"', POPUP_HTML))
        missing = sorted(referenced - present)
        assert not missing, (
            "popup.js references elements that popup.html does not define; "
            f"bindEvents() throws on the first one: {missing}"
        )

    def test_handlers_bound_in_bind_events_have_their_element(self):
        block = POPUP_JS.split("function bindEvents()", 1)[1].split("\nfunction ", 1)[0]
        for element_id in re.findall(r"getElementById\(['\"]([A-Za-z0-9_-]+)['\"]\)", block):
            assert f'id="{element_id}"' in POPUP_HTML, f"bindEvents binds #{element_id}, absent from popup.html"

    def test_every_tab_has_a_panel(self):
        tabs = set(re.findall(r'data-tab="([a-z]+)"', POPUP_HTML))
        panels = set(re.findall(r'id="panel-([a-z]+)"', POPUP_HTML))
        assert tabs, "no tab declared"
        assert tabs == panels, f"tabs {sorted(tabs)} != panels {sorted(panels)}"

    def test_hidden_class_is_styled(self):
        assert re.search(r"\.hidden\s*\{[^}]*display:\s*none", POPUP_CSS), (
            "the popup toggles elements with the `hidden` class; it must be defined in the CSS"
        )


class TestManifest:
    def test_permissions_cover_the_apis_used(self):
        declared = set(MANIFEST.get("permissions", []))
        used = set()
        for path in js_files():
            used |= set(re.findall(r"chrome\.[a-z]+", path.read_text()))
        needed = {REQUIRED_PERMISSIONS[api] for api in used if api in REQUIRED_PERMISSIONS}
        assert needed <= declared, f"missing permissions: {sorted(needed - declared)}"

    def test_manifest_version_and_popup(self):
        assert MANIFEST["manifest_version"] == 3
        assert MANIFEST["action"]["default_popup"].endswith("popup.html")
        assert (EXTENSION / MANIFEST["action"]["default_popup"]).exists()

    def test_service_worker_file_exists(self):
        worker = MANIFEST["background"]["service_worker"]
        assert (EXTENSION / worker).exists()

    def test_declared_scripts_exist(self):
        for entry in MANIFEST.get("content_scripts", []):
            for script in entry["js"]:
                assert (EXTENSION / script).exists()


class TestApiBase:
    def test_popup_targets_an_https_endpoint(self):
        match = re.search(r"API_BASE\s*=\s*['\"]([^'\"]+)['\"]", POPUP_JS)
        assert match, "API_BASE not found in popup.js"
        assert match.group(1).startswith("https://"), (
            "the popup sends a bearer token: it must not travel over plain HTTP"
        )

    def test_tabs_are_asked_for_without_the_tabs_permission_trap(self):
        """`tab.url` is read for the cache key: with activeTab only, that is allowed on the
        tab the user invoked the extension on — which is exactly the popup's case."""
        assert "chrome.tabs.query" in POPUP_JS
        assert "activeTab" in MANIFEST["permissions"]
