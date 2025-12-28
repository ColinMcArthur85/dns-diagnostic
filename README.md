# DNS Diagnostic Tool (Phase 1)

## Overview
A deterministic, rules-based domain analyzer for AttractWell and GetOiling.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Run the tool from the command line:

```bash
python3 src/main.py --domain example.com --platform attractwell
```

### Options
- `--domain`: The domain to analyze (e.g., `example.com` or `shop.example.com`)
- `--platform`: Target platform (`attractwell` or `getoiling`)
- `--has-external`: Set if the user has external dependencies (default: False)
- `--email-managed`: Set if email is managed by the platform (default: False)
- `--comfortable`: Set if user is comfortable editing DNS (default: False)
- `--registrar-known`: Set if user knows their registrar (default: False)

## Output
Returns a JSON object with:
- DNS snapshot
- Email state
- Connection options
- Recommended actions
- Warnings
