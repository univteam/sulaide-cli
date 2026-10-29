from _fake import FakeClientCase


class SourceOptionTests(FakeClientCase):
    def test_projects_create_language(self):
        self.cli("projects", "create", "--title", "Deck", "--language", "en", "--request-id", "r1")
        self.assertEqual(self.body(), {"request_id": "r1", "title": "Deck", "language": "en"})

    def test_source_set_sends_all_web_options(self):
        self.cli("source", "set", "3", "--text", "底稿", "--request-id", "s1", "--title", "Q2", "--language", "en",
                 "--target-pages", "8", "--narrative", "fluent", "--style-id", "5", "--source-page-count", "12")
        body = self.body()
        self.assertEqual(self.calls[-1][:2], ("PUT", "/projects/3/source"))
        self.assertEqual({k: body[k] for k in ("project_title", "language", "target_page_count", "narrative_preference",
                                               "style_id", "source_page_count")},
                         {"project_title": "Q2", "language": "en", "target_page_count": 8,
                          "narrative_preference": "fluent_expression", "style_id": 5, "source_page_count": 12})
        self.assertNotIn("page_count", body)

    def test_source_omits_unset_options_including_narrative(self):
        self.cli("source", "set", "3", "--text", "x", "--request-id", "s2")
        body = self.body()
        for key in ("project_title", "language", "target_page_count", "narrative_preference",
                    "style_id", "source_page_count", "page_count"):
            self.assertNotIn(key, body)

    def test_narrative_is_sent_only_when_set(self):
        self.cli("source", "set", "3", "--text", "x", "--narrative", "rigorous")
        self.assertEqual(self.body()["narrative_preference"], "rigorous_structure")
        self.cli("source", "upload", "3", __file__, "--narrative", "fluent")
        self.assertEqual(self.body()["narrative_preference"], "fluent_expression")
        self.cli("source", "upload", "3", __file__)
        self.assertNotIn("narrative_preference", self.body())

    def test_clear_style_is_explicit_and_exclusive(self):
        self.cli("source", "set", "3", "--text", "x", "--clear-style")
        self.assertIsNone(self.body()["style_id"])
        with self.assertRaises(SystemExit):
            self.cli("source", "set", "3", "--text", "x", "--clear-style", "--style-id", "5")
        self.cli("source", "upload", "3", __file__, "--clear-style")
        self.assertIsNone(self.body()["style_id"])

    def test_preview_passes_reviewed_identity(self):
        self.cli("preview", "generate", "3", "--expected-version", "9",
                 "--expected-source-revision", "4", "--expected-editing-version", "10",
                 "--expected-manifest-revision", "2")
        self.assertEqual({k: v for k, v in self.body().items() if k != "request_id"}, {
            "expected_presentation_version_id": 9, "expected_source_revision": 4,
            "expected_editing_version_id": 10, "expected_manifest_revision": 2})

    def test_legacy_preview_omits_new_guards(self):
        self.cli("preview", "generate", "3")
        self.assertEqual({k: v for k, v in self.body().items() if k != "request_id"},
                         {"expected_presentation_version_id": None})

    def test_target_pages_range(self):
        with self.assertRaises(ValueError):
            self.cli("source", "set", "3", "--text", "x", "--target-pages", "51")

    def test_analysis_structure_requirements(self):
        self.cli("analysis", "start", "3", "--request-id", "a1", "--page-count", "6",
                 "--structure-requirements", "合并产品与服务")
        self.assertEqual(self.body()["structure_requirements"], "合并产品与服务")
        self.assertEqual(self.body()["page_count"], 6)
        self.cli("analysis", "start", "3", "--request-id", "a2")
        self.assertNotIn("structure_requirements", self.body())

    def test_page_count_range(self):
        for count in (0, 51, -1):
            with self.assertRaises(ValueError):
                self.cli("analysis", "start", "3", "--page-count", str(count))
        self.cli("analysis", "start", "3", "--page-count", "1")
        self.assertEqual(self.body()["page_count"], 1)
        self.cli("analysis", "start", "3", "--page-count", "50")
        self.assertEqual(self.body()["page_count"], 50)

    def test_styles_list(self):
        self.responses = {("GET", "/styles"): {"items": [{"id": 5, "name": "Brand"}]}}
        self.assertEqual(self.cli("styles", "list")["items"][0]["id"], 5)
