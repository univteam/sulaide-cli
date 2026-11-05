"""Public, bounded text contract for CLI-supplied visual specifications.

This module contains the data format only; generation instructions stay on the
service. Keep the public golden fixtures in sync with the service contract.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

SCHEMA_VERSION = "brand-spec.v1"
MAX_CHARACTERS = 3000
MAX_BYTES = 12003
_COLORS = ("Primary color", "Secondary color", "Accent color", "Text color")
_DERIVED = ("Background color", "Card color", "Stroke color", "Chart data series colors")
_FONTS = ("Title font", "Subtitle font")
_TEXT_LIMITS = {"Color scheme": 80, "Company/Brand": 120, "Template theme": 400}
_HEX = re.compile(r"#[0-9A-Fa-f]{6}\Z")
_FONT = re.compile(r"(.+), size: ([1-9][0-9]{0,2})pt, weight: (normal|semibold|bold)\Z")


def _invalid(reason: str) -> ValueError:
    return ValueError(f"invalid_brand_spec:{reason}")


def _hex(value: str) -> str:
    if not _HEX.fullmatch(value):
        raise _invalid("color")
    return value.upper()


def _mix(color: str, white_ratio: float) -> str:
    return "#" + "".join(
        f"{round(int(color[i:i + 2], 16) * (1 - white_ratio) + 255 * white_ratio):02X}"
        for i in (1, 3, 5)
    )


def _white_contrast(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return 1.05 / (.2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2] + .05)


def _parse_fields(text: str, schema_version: str) -> dict:
    if schema_version != SCHEMA_VERSION or not isinstance(text, str):
        raise _invalid("schema_or_type")
    try:
        if len(text.encode("utf-8")) > MAX_BYTES:
            raise _invalid("byte_limit")
    except UnicodeEncodeError as exc:
        raise _invalid("encoding") from exc
    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if any(c != "\n" and unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in text):
        raise _invalid("control_character")
    if any(token in text.lower() for token in ("base64,", "http://", "https://", "```", "{" , "}")):
        raise _invalid("non_data_content")
    values: dict = {}
    phase = "start"
    headers: set[str] = set()
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line in ("[Color Palette]", "[Typography]"):
            if line in headers or (line == "[Color Palette]" and phase != "start") or (line == "[Typography]" and phase != "palette"):
                raise _invalid("section_order")
            headers.add(line)
            phase = "palette" if line == "[Color Palette]" else "typography"
            continue
        if phase in {"start", "done"} or ": " not in line:
            raise _invalid("field_or_section")
        label, value = line.split(": ", 1)
        value = value.strip()
        if label in values or not value:
            raise _invalid("duplicate_or_empty_field")
        if label in _COLORS or label in _DERIVED or label == "Color scheme":
            if phase != "palette":
                raise _invalid("field_section")
        elif label in _FONTS:
            if phase != "typography":
                raise _invalid("field_section")
        elif label in {"Company/Brand", "Template theme"}:
            if phase not in {"typography", "tail"}:
                raise _invalid("field_section")
            phase = "done" if label == "Template theme" else "tail"
        else:
            raise _invalid("unknown_field")
        if label in _COLORS or label in _DERIVED[:-1]:
            values[label] = _hex(value)
        elif label == "Chart data series colors":
            values[label] = tuple(_hex(c.strip()) for c in value.split(","))
        elif label in _FONTS:
            match = _FONT.fullmatch(value)
            if not match:
                raise _invalid("font")
            family, size, weight = match.groups()
            family = family.strip()
            if not 1 <= len(family) <= 100 or any(t in family for t in (", size:", ", weight:")) or not 1 <= int(size) <= 200:
                raise _invalid("font")
            values[label] = (family, int(size), weight)
        else:
            if len(value) > _TEXT_LIMITS[label]:
                raise _invalid("field_length")
            values[label] = value
    if set(_COLORS + _FONTS + ("Template theme",)) - values.keys() or len(headers) != 2:
        raise _invalid("missing_field")
    if _white_contrast(values["Text color"]) < 4.5:
        raise _invalid("text_contrast")
    base = [values[label] for label in _COLORS[:3]]
    expected = {
        "Background color": "#FFFFFF",
        "Card color": _mix(base[0], .93),
        "Stroke color": _mix(base[0], .78),
        "Chart data series colors": tuple(dict.fromkeys(base + [_mix(c, .28) for c in base])),
    }
    for key, value in expected.items():
        if key in values and values[key] != value:
            raise _invalid("derived_color_mismatch")
        values[key] = value
    return values


def _canonical_text(values: dict) -> str:
    lines = ["[Color Palette]"]
    if "Color scheme" in values:
        lines.append("Color scheme: " + values["Color scheme"])
    for key in _COLORS + _DERIVED:
        value = values[key]
        lines.append(f"{key}: {', '.join(value) if isinstance(value, tuple) else value}")
    lines.append("[Typography]")
    for key in _FONTS:
        family, size, weight = values[key]
        lines.append(f"{key}: {family}, size: {size}pt, weight: {weight}")
    for key in ("Company/Brand", "Template theme"):
        if key in values:
            lines.append(f"{key}: {values[key]}")
    text = "\n".join(lines)
    if len(text) > MAX_CHARACTERS:
        raise _invalid("character_limit")
    return text


def normalize_brand_spec(text: str, schema_version: str = SCHEMA_VERSION) -> dict:
    values = _parse_fields(text, schema_version)
    canonical = _canonical_text(values)
    return {
        "schema_version": SCHEMA_VERSION,
        "text": canonical,
        "spec_hash": hashlib.sha256((SCHEMA_VERSION + "\n" + canonical).encode("utf-8")).hexdigest(),
    }


def read_brand_spec(path: Path) -> dict:
    with Path(path).open("rb") as file:
        data = file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise _invalid("byte_limit")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _invalid("encoding") from exc
    return normalize_brand_spec(text)
