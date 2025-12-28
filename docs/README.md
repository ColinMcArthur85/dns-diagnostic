# Docs

Guidelines and examples for maintaining this DNS diagnostic tool.

## Markdown rules

- Keep files in plain Markdown; avoid embedded HTML unless necessary.
- Use ASCII where possible; keep lines under ~120 chars when practical.
- Prefer tables for DNS record examples; use fenced code blocks for commands.
- Include context (domain, platform) and expected outputs when documenting examples.

## Examples

- CLI run:
  ```bash
  python3 src/main.py --domain example.com --platform attractwell
  ```
- Sample DNS table (what the tool returns):
  | Record | Value |
  | --- | --- |
  | A | 199.189.226.101 |
  | CNAME www | example.com |
  | MX | aspmx.l.google.com. (priority 1) |
  | TXT SPF | v=spf1 include:\_spf.google.com ~all |
  | DMARC | v=DMARC1; p=reject |
