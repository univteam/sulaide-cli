import hashlib
import json
from pathlib import Path
import unittest

from sulaide_cli.brand_spec import normalize_brand_spec

FIXTURE = json.loads((Path(__file__).parent / "fixtures/brand_spec_v1.json").read_text())


class BrandSpecContractTests(unittest.TestCase):
    def base(self):
        return FIXTURE["valid"][0]["input"]

    def test_public_golden_fixtures(self):
        for fixture in FIXTURE["valid"]:
            with self.subTest(fixture["name"]):
                actual = normalize_brand_spec(fixture["input"])
                self.assertEqual(actual["schema_version"], FIXTURE["schema_version"])
                self.assertEqual(actual["text"], fixture["canonical_text"])
                self.assertEqual(actual["spec_hash"], fixture["spec_hash"])
                self.assertEqual(normalize_brand_spec(actual["text"])["text"], actual["text"])

    def test_invalid_golden_fixtures(self):
        for fixture in FIXTURE["invalid"]:
            with self.subTest(fixture["name"]), self.assertRaises(ValueError):
                normalize_brand_spec(fixture["input"])

    def test_equivalent_transport_and_hex_normalization(self):
        original = normalize_brand_spec(self.base())
        variant = "\ufeff" + self.base().replace("#E08020", "#e08020").replace("\n", "\r\n") + "\r\n"
        self.assertEqual(normalize_brand_spec(variant), original)

    def test_rejects_bad_headers_values_and_transport(self):
        variants = [
            self.base().replace("[Typography]", "[Other]"),
            self.base().replace("Primary color:", "primary color:"),
            self.base().replace("32pt", "201pt"),
            self.base().replace("32pt", "32.5pt"),
            self.base().replace("weight: bold", "weight: heavy"),
            self.base().replace("Arial, size:", "Arial, size: other, size:"),
            self.base().replace("Arial", "A" * 101),
            self.base().replace("#123456", "123456"),
            self.base() + "\n# comment", "```text\n" + self.base() + "\n```",
            self.base().replace("Example", "data:image/png;base64,AAAA"),
            self.base().replace("Example", "https://example.com"),
            self.base().replace("Example", "{system_prompt}"),
            self.base().replace("Example", "Ex\x00ample"),
            self.base().replace("Example", "Ex\u200bample"),
            self.base().replace("Example", "X" * 121),
            self.base().replace("Clear evidence and restrained visual hierarchy.", "主" * 401),
            "", None, "\n" * 12004 + self.base(),
        ]
        for variant in variants:
            with self.subTest(repr(variant)[:80]), self.assertRaises(ValueError):
                normalize_brand_spec(variant)
        with self.assertRaises(ValueError):
            normalize_brand_spec(self.base(), schema_version="brand-spec.v2")

    def test_rejects_changed_explicit_derived_fields(self):
        text = normalize_brand_spec(self.base())["text"]
        for label in ("Background color", "Card color", "Stroke color", "Chart data series colors"):
            changed = "\n".join(label + ": #000000" if line.startswith(label + ":") else line for line in text.splitlines())
            with self.subTest(label), self.assertRaises(ValueError):
                normalize_brand_spec(changed)

    def test_no_implicit_optional_brand_or_color_scheme(self):
        text = "\n".join(line for line in self.base().splitlines() if not line.startswith(("Color scheme:", "Company/Brand:")))
        result = normalize_brand_spec(text)
        self.assertNotIn("Company/Brand:", result["text"])
        self.assertNotIn("Color scheme:", result["text"])

    def test_unicode_text_identity_uses_utf8(self):
        actual = normalize_brand_spec(self.base().replace("Example", "示例品牌"))
        self.assertEqual(actual["spec_hash"], hashlib.sha256(("brand-spec.v1\n" + actual["text"]).encode("utf-8")).hexdigest())


class ReadBrandSpecTests(unittest.TestCase):
    def test_read_only_public_result_and_utf8_bom(self):
        import tempfile
        from sulaide_cli.brand_spec import read_brand_spec
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brand.txt"
            path.write_bytes(("\ufeff" + FIXTURE["valid"][0]["input"]).encode())
            result = read_brand_spec(path)
            self.assertEqual(set(result), {"schema_version", "text", "spec_hash"})
            self.assertEqual(result["spec_hash"], FIXTURE["valid"][0]["spec_hash"])
            self.assertNotIn(str(path), result["text"])

    def test_bounded_read_and_encoding(self):
        import tempfile
        from sulaide_cli.brand_spec import read_brand_spec, MAX_BYTES
        text = FIXTURE["valid"][0]["input"]
        exact = text.encode() + b"\n" * (MAX_BYTES - len(text.encode()))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brand.txt"
            path.write_bytes(exact)
            self.assertEqual(read_brand_spec(path)["spec_hash"], FIXTURE["valid"][0]["spec_hash"])
            path.write_bytes(exact + b"\n")
            with self.assertRaises(ValueError):
                read_brand_spec(path)
            path.write_bytes(b"\xff\xfe")
            with self.assertRaises(ValueError):
                read_brand_spec(path)
            with self.assertRaises(FileNotFoundError):
                read_brand_spec(Path(directory) / "missing.txt")

    def test_client_carries_no_service_instruction_prose(self):
        result = normalize_brand_spec(FIXTURE["valid"][0]["input"])
        self.assertEqual(set(result), {"schema_version", "text", "spec_hash"})
        self.assertNotIn("Strictly use", result["text"])
        self.assertNotIn("never ordinary text", result["text"])
