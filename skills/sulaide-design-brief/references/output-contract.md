# Public specification contract: brand-spec.v1

Write UTF-8 plain text, without Markdown fences, commentary or citations. This is a field protocol, not a copy of Sulaide's private generation prompts. The CLI submits the text with `schema_version: brand-spec.v1`.

```text
[Color Palette]
Primary color: #153B5B
Secondary color: #2251FF
Accent color: #E69A32
Text color: #111111

[Typography]
Title font: Arial, size: 30pt, weight: bold
Subtitle font: Arial, size: 20pt, weight: normal
Company/Brand: Example Company
Template theme: Restrained enterprise reporting with clear hierarchy and generous whitespace
```

Required blocks and fields, in order:

- `[Color Palette]`: `Primary color`, `Secondary color`, `Accent color`, `Text color`; each is a six-digit HEX colour. `Color scheme` is an optional name of at most 80 characters, placed before Primary color.
- `[Typography]`: `Title font` and `Subtitle font`, each exactly `family, size: integerpt, weight: weight`. A family is one nonempty line of at most 100 characters and cannot contain the reserved separators `, size:` or `, weight:`. Integer sizes are 1–200; weights are `normal`, `semibold` or `bold`.
- Optional `Company/Brand`, at most 120 characters, only when supported by the user's materials or instruction.
- Required `Template theme`, one line of at most 400 characters describing visual character. Do not include URLs, source analysis, placeholders or instructions to execute a product stage.

Labels and block names are case-sensitive. Reject unknown/duplicate fields, comments, fenced blocks, control characters, inline Base64 and placeholders. Blank lines may separate blocks. Colour case and outer whitespace are normalised.

The white background is fixed. Text must have a contrast ratio of at least 4.5 against white. If the source uses a dark background or low-contrast text, record that fact separately and make the proposed adaptation clear before using it. Do not claim adaptation is an exact extraction.

`Background color`, `Card color`, `Stroke color` and `Chart data series colors` may be omitted. The CLI normaliser adds white background and the existing derived palette. If you provide them, they must match the derived values; arbitrary decorative colours are rejected. Do not manually invent a different derivation.

The canonical representation uses fixed field order, LF newlines, uppercase HEX, trimmed outer field whitespace and no final newline. Only a leading UTF-8 BOM is removed. The CLI reads at most 12003 bytes including an optional BOM; canonical public text and the server's effective text must each fit 3000 Unicode code points. Oversized input fails rather than being truncated.

The receipt's public `spec_hash` is SHA-256 of UTF-8(`brand-spec.v1` + LF + canonical text). The server also freezes an effective-specification hash; this is distinct from the public hash. Private fixed prompt instructions are assembled on the server and never belong in this file or skill package.
