# Agent Framework: DNS Diagnostic Tool

A guide for AI agents and developers working on the DNS Diagnostic Tool.

## 1. Project Overview

A hybrid application for diagnosing DNS configurations and providing guided setup plans for AttractWell and GetOiling platforms.

- **Frontend**: Next.js (TypeScript, Tailwind CSS v4, Framer Motion) in `/ui`
- **Backend**: Python CLI engine in `/src` for deterministic diagnostics and AI-driven insights
- **Integration**: UI calls Python engine via `execFile()` in Next.js API routes
- **Truth Source**: `domain_rules.yaml` contains all platform logic and DNS rules

### Core Philosophy
- **Deterministic Core**: All diagnostic decisions are rules-based from `domain_rules.yaml`
- **AI Translation**: AI translates structured JSON into human-friendly explanations
- **AI is a translator, not a decision-maker**: Never let AI infer DNS records

## 2. Build and Test Commands

### Backend (Python)
```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# CLI Usage
python3 src/main.py --domain example.com --platform attractwell --ai

# Testing
python3 -m pytest tests/test_core.py -v
```

### Frontend (Next.js)
```bash
cd ui
npm install
npm run dev     # http://localhost:3000
npm run build   # Production build
npm run lint    # Lint check
```

## 3. Code Style Guidelines

- **Minimal Commenting**: Only comment complex blocks; code should be self-documenting

### Python (Backend)
- **Modular Design**: `dns_lookup.py` (queries), `decision_engine.py` (logic), `action_plan_builder.py` (output)
- **Entry Point**: `main.py` outputs JSON to stdout, logs/errors to stderr
- **Config-Driven**: Never hardcode DNS records; use `ConfigLoader`

### TypeScript/React (Frontend)
- **Theme**: Dark "Antigravity" theme with `framer-motion` animations
- **CSS**: Tailwind v4 utilities + semantic classes in `globals.css`
- **State**: React hooks for local state; graceful loading/error handling

## 4. Security Controls (MANDATORY)

All security vulnerabilities have been addressed. **Do not regress these controls.**

### API Layer (`ui/src/app/api/`)
| Control | Implementation | File |
|---------|----------------|------|
| Command Injection Prevention | `execFile()` with array args | All routes |
| Input Validation | RFC 1035 regex, whitelists | All routes |
| SSRF Protection | Blocked internal domains | `diagnose/route.ts` |
| Rate Limiting | Per-IP limits | `lib/rate-limiter.ts` |
| Session Management | TTL, max count, cleanup | `chat/route.ts` |
| Error Sanitization | No path leakage | All routes |

### DNS Layer (`src/dns_lookup.py`)
| Control | Value | Purpose |
|---------|-------|---------|
| `DEFAULT_TIMEOUT` | 5.0s | Per-server timeout |
| `DEFAULT_LIFETIME` | 15.0s | Total query timeout |
| `MAX_RECORDS_PER_TYPE` | 100 | Prevent memory exhaustion |
| `CNAME_DEPTH_LIMIT` | 5 | Prevent infinite loops |
| Domain validation | RFC 1035 | Block malformed input |
| SSRF blocking | Internal TLDs | Block `.local`, `.corp`, etc. |

### Rate Limits
- Diagnose endpoint: 10 requests/minute per IP
- Chat endpoint: 30 requests/minute per IP

## 5. Testing Instructions

- **Logic Changes**: Update tests in `tests/test_core.py`
- **Mocking**: Use fixtures in `tests/fixtures/`
- **UI Verification**: Check "Action Plan" and "AI Insights" render correctly
- **Security**: Never bypass input validation or rate limiting

## 6. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/diagnose` | POST | Run DNS diagnostic |
| `/api/chat` | POST | Conversational AI chat |
| `/api/health` | GET | Health check for monitoring |

## 7. Environment Variables

```bash
# Required for AI features
OPENAI_API_KEY=sk-...
```

Store in `.env` file (never commit to git).