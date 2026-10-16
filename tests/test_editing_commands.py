import tempfile
from pathlib import Path
from unittest.mock import patch

from _fake import FakeClientCase


class PreviewEditingCommandTests(FakeClientCase):
    def test_visual_styles_layout_and_export_check(self):
        self.cli("visual-styles", "list")
        self.cli("layout", "show", "3")
        self.cli("export", "check", "3", "--version-id", "10", "--manifest-hash", "h")
        self.assertEqual([c[:2] for c in self.calls], [("GET", "/visual-styles"), ("GET", "/projects/3/layout"),
                                                       ("GET", "/projects/3/export-check")])
        self.assertEqual(self.calls[-1][2]["params"], {"version_id": 10, "manifest_hash": "h"})

    def test_theme(self):
        self.cli("theme", "set", "3", "--primary", "#112233", "--apply-section-template", "--expected-version", "10")
        self.assertEqual(self.calls[-1][:2], ("POST", "/projects/3/theme"))
        body = self.body()
        self.assertEqual((body["primary"], body["apply_latest_section_template"], body["expected_presentation_version_id"]),
                         ("#112233", True, 10))
        with self.assertRaises(ValueError):
            self.cli("theme", "set", "3")

    def test_regenerate_and_edit_image(self):
        self.cli("pages", "regenerate", "3", "2", "--prompt", "简洁", "--visual-style", "luxury_brand")
        self.assertEqual(self.calls[-1][:2], ("POST", "/projects/3/pages/2/regenerate"))
        self.assertEqual({k: self.body()[k] for k in ("prompt", "visual_style_id")}, {"prompt": "简洁", "visual_style_id": "luxury_brand"})
        with tempfile.TemporaryDirectory() as tmp:
            ref = Path(tmp) / "ref.png"; ref.write_bytes(b"\x89PNG")
            self.cli("pages", "edit-image", "3", "2", "--prompt", "蓝色", "--reference-image", str(ref))
        self.assertTrue(self.body()["reference_image"].startswith("data:image/png;base64,"))

    def test_images_and_restore(self):
        self.cli("pages", "images", "3", "s1")
        self.assertEqual(self.calls[-1][:2], ("GET", "/projects/3/pages/s1/image-versions"))
        self.cli("pages", "restore-image", "3", "s1", "--source-version", "8", "--version-id", "10", "--manifest-hash", "h")
        self.assertEqual({k: self.body()[k] for k in ("source_version_id", "expected_presentation_version_id", "expected_manifest_hash")},
                         {"source_version_id": 8, "expected_presentation_version_id": 10, "expected_manifest_hash": "h"})


class LayoutEditingCommandTests(FakeClientCase):
    def test_edit_fields(self):
        self.cli("pages", "edit", "3", "1", "--title", "新", "--visual-style", "luxury_brand", "--title-width", "800",
                 "--expected-version", "10", "--expected-revision", "3")
        self.assertEqual(self.calls[-1][:2], ("PATCH", "/projects/3/pages/1"))
        body = self.body()
        self.assertEqual({k: body[k] for k in ("title", "visual_style_id", "title_width", "expected_presentation_version_id",
                                               "expected_manifest_revision")},
                         {"title": "新", "visual_style_id": "luxury_brand", "title_width": 800.0,
                          "expected_presentation_version_id": 10, "expected_manifest_revision": 3})
        with self.assertRaises(ValueError):
            self.cli("pages", "edit", "3", "1")

    def test_page_list_commands(self):
        self.cli("pages", "add", "3", "--after", "2", "--title", "T")
        self.cli("pages", "delete", "3", "2")
        self.cli("pages", "duplicate", "3", "1")
        self.cli("pages", "move", "3", "2", "up")
        self.cli("pages", "reanalyze", "3", "1", "--instruction", "突出数据")
        self.assertEqual([c[:2] for c in self.calls], [
            ("POST", "/projects/3/pages"), ("POST", "/projects/3/pages/2/delete"),
            ("POST", "/projects/3/pages/1/duplicate"), ("POST", "/projects/3/pages/2/move"),
            ("POST", "/projects/3/pages/1/reanalyze")])
        self.assertEqual(self.body(3)["direction"], "up")
        self.assertEqual(self.body(0)["after_page"], 2)

    def test_request_id_is_bound_to_body(self):
        self.cli("pages", "edit", "3", "1", "--title", "A")
        self.cli("pages", "edit", "3", "1", "--title", "B")
        self.assertNotEqual(self.body(0)["request_id"], self.body(1)["request_id"])

    def test_split_waits_then_applies(self):
        polls = iter([{"status": "running"}, {"status": "succeeded"}])
        self.responses = {
            ("POST", "/projects/3/pages/1/split"): {"run_id": "tr", "presentation_version_id": 10, "manifest_revision": 3},
            ("GET", "/projects/3/structure-runs/tr"): lambda kw: next(polls),
            ("POST", "/projects/3/structure-runs/tr/apply"): {"presentation_version_id": 11},
        }
        with patch("sulaide_cli.cli.time.sleep"):
            result = self.cli("pages", "split", "3", "1", "--at", "40")
        self.assertEqual(result["presentation_version_id"], 11)
        self.assertEqual(self.body(0)["split_offset"], 40)
        apply = self.body(-1)
        self.assertEqual({k: apply[k] for k in ("run_id", "kind", "page_number", "split_offset",
                                                "expected_presentation_version_id", "expected_manifest_revision")},
                         {"run_id": "tr", "kind": "split", "page_number": 1, "split_offset": 40,
                          "expected_presentation_version_id": 10, "expected_manifest_revision": 3})

    def test_merge_no_wait(self):
        self.responses = {("POST", "/projects/3/pages/2/merge"): {"run_id": "tr"}}
        self.cli("pages", "merge", "3", "2", "--no-wait")
        self.assertEqual(len(self.calls), 1)

    def test_failed_title_run_raises(self):
        from sulaide_cli.cli import ApiError
        self.responses = {("POST", "/projects/3/pages/2/merge"): {"run_id": "tr"},
                          ("GET", "/projects/3/structure-runs/tr"): {"status": "failed"}}
        with self.assertRaises(ApiError):
            self.cli("pages", "merge", "3", "2")
