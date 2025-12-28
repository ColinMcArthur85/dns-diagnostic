# Config

Platform constants and provider fingerprints live in the root file: domain_rules.yaml.

## Contents

- domain_rules.yaml (in repository root)
  - Platform DNS targets (nameservers, A/CNAME targets)
  - Decision rules (option selection)
  - Email provider fingerprints (MX patterns) and SPF/DMARC identifiers

## Editing guidance

- Treat domain_rules.yaml as the single source of truth; update it when DNS targets or rules change.
- After edits, run the test suite:
  ```bash
  python3 -m pytest tests/test_core.py -v
  ```
- Consider adding a short change note to the README or this file when targets change (e.g., IP updates).
