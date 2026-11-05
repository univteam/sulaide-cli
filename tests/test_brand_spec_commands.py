from pathlib import Path
from unittest.mock import patch

from _fake import FakeClientCase


TEXT = '''[Color Palette]
Primary color: #123456
Secondary color: #2251FF
Accent color: #00A9F4
Text color: #111111

[Typography]
Title font: Arial, size: 30pt, weight: bold
Subtitle font: Arial, size: 20pt, weight: normal
Template theme: Clear enterprise report
'''
CAPABILITY = {"brand_spec_override": {"schema_versions": ["brand-spec.v1"], "max_characters": 3000,
                                      "operations": ["preview_start", "preview_continue", "page_regenerate"]}}


class BrandSpecCommandTests(FakeClientCase):
    def setUp(self):
        super().setUp()
        self.file = Path(self.tmp.name) / "brand.txt"
        self.file.write_text(TEXT, encoding="utf-8")
        self.responses = {("GET", "/capabilities"): CAPABILITY}

    def accepted(self, path):
        def handler(kwargs):
            from sulaide_cli.brand_spec import normalize_brand_spec
            spec = normalize_brand_spec(kwargs["json_body"]["brand_spec_override"]["text"])
            return {"operation": {"operation_id": "op-brand"}, "presentation_version_id": 20,
                    "brand_spec": {"source": "cli_override", "schema_version": "brand-spec.v1",
                                             "spec_hash": spec["spec_hash"]}}
        self.responses[("POST", path)] = handler

    def test_new_run_sends_normalized_text_to_start_with_review_identity(self):
        self.accepted("/projects/3/preview/start")
        result = self.cli("preview", "generate", "3", "--brand-spec", str(self.file), "--new-run",
                          "--expected-version", "10", "--expected-source-revision", "4")
        self.assertEqual(result["presentation_version_id"], 20)
        self.assertEqual(self.calls[0][:2], ("GET", "/capabilities"))
        self.assertEqual(self.calls[-1][:2], ("POST", "/projects/3/preview/start"))
        body = self.body()
        self.assertEqual(set(body["brand_spec_override"]), {"schema_version", "text"})
        self.assertNotIn(str(self.file), str(body))
        self.assertEqual(body["expected_presentation_version_id"], 10)
        self.assertEqual(body["expected_source_revision"], 4)

    def test_continue_and_single_page_regenerate_support_explicit_spec(self):
        for argv, path in ((["preview", "generate", "3"], "/projects/3/preview/continue"),
                           (["pages", "regenerate", "3", "2"], "/projects/3/pages/2/regenerate")):
            self.accepted(path)
            self.cli(*argv, "--brand-spec", str(self.file), "--request-id", "explicit-request")
            self.assertEqual(self.calls[-1][:2], ("POST", path))
            self.assertEqual(self.body()["request_id"], "explicit-request")

    def test_old_requests_do_not_probe_capabilities_or_send_spec(self):
        self.cli("preview", "generate", "3")
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("brand_spec_override", self.body())
        self.calls.clear()
        self.cli("pages", "regenerate", "3", "2")
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("brand_spec_override", self.body())

    def test_new_run_requires_spec_before_any_request(self):
        with self.assertRaises(ValueError):
            self.cli("preview", "generate", "3", "--new-run")
        self.assertEqual(self.calls, [])

    def test_capability_missing_prevents_generation(self):
        self.responses[("GET", "/capabilities")] = {}
        with self.assertRaisesRegex(ValueError, "规范|brand"):
            self.cli("preview", "generate", "3", "--brand-spec", str(self.file))
        self.assertEqual([c[0] for c in self.calls], ["GET"])

    def test_missing_file_prevents_all_network_calls(self):
        with self.assertRaises(OSError):
            self.cli("preview", "generate", "3", "--brand-spec", str(self.file.with_name("missing")))
        self.assertEqual(self.calls, [])

    def test_mismatched_adoption_fails_without_retry(self):
        path = "/projects/3/preview/continue"
        self.responses[("POST", path)] = {"operation": {"operation_id": "op-brand"},
            "brand_spec": {"source": "cli_override", "spec_hash": "wrong"}}
        with self.assertRaisesRegex(ValueError, "采用|hash"):
            self.cli("preview", "generate", "3", "--brand-spec", str(self.file))
        self.assertEqual(sum(c[0] == "POST" for c in self.calls), 1)

    def test_lost_ack_identity_depends_on_content_and_endpoint_not_file_path(self):
        # A failed write retains its ID; successful writes intentionally release it.
        ids = []
        def lost(kwargs):
            ids.append(kwargs["json_body"]["request_id"])
            raise OSError("lost ACK")
        for endpoint in ("start", "continue"):
            self.responses[("POST", f"/projects/3/preview/{endpoint}")] = lost
        for file, new in ((self.file, False), (self.file.with_name("copy.txt"), False), (self.file, True)):
            file.write_text(TEXT, encoding="utf-8")
            with self.assertRaises(OSError):
                self.cli("preview", "generate", "3", "--brand-spec", str(file), *(["--new-run"] if new else []))
        self.assertEqual(ids[0], ids[1])
        self.assertNotEqual(ids[1], ids[2])
        self.file.write_text(TEXT.replace("enterprise", "annual"), encoding="utf-8")
        with self.assertRaises(OSError):
            self.cli("preview", "generate", "3", "--brand-spec", str(self.file))
        self.assertNotEqual(ids[0], ids[-1])
