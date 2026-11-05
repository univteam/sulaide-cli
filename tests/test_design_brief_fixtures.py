"""Verify the facts offered to a real host; this does not test host judgement."""
import json
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).parent / "fixtures/design_brief"
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


class DesignBriefFixtureTests(unittest.TestCase):
    def test_pptx_contains_actual_typographic_evidence(self):
        expected = json.loads((ROOT / "expected.json").read_text())["pptx"]
        with ZipFile(ROOT / "brand-reference.pptx") as bundle:
            slide = ET.fromstring(bundle.read("ppt/slides/slide1.xml"))
        runs = slide.findall(".//a:r", NS)
        self.assertEqual([r.find("a:rPr", NS).get("sz") for r in runs],
                         [str(expected["title_size_pt"] * 100), str(expected["subtitle_size_pt"] * 100)])
        self.assertEqual([r.find("a:rPr/a:latin", NS).get("typeface") for r in runs], ["Arial", "Arial"])
        colours = {node.get("val") for node in slide.findall(".//a:srgbClr", NS)}
        for key in ("primary", "secondary", "accent", "text_color"):
            self.assertIn(expected[key][1:], colours)

    def test_screenshot_does_not_supply_measured_font_metadata(self):
        expected = json.loads((ROOT / "expected.json").read_text())["screenshot"]
        self.assertEqual(expected["font_family"], "unknown")
        self.assertEqual(expected["font_size_pt"], "unknown")
        data = (ROOT / "reference-screenshot.png").read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertLess(len(data), 200_000)

    def test_secondary_document_contains_real_conflicting_evidence(self):
        with ZipFile(ROOT / "conflicting-guide.docx") as bundle:
            xml = bundle.read("word/document.xml").decode()
        self.assertIn('w:ascii="Times New Roman"', xml)
        self.assertIn('w:val="B01038"', xml)
        self.assertIn('w:val="80"', xml)  # OOXML half-points: 40pt.
