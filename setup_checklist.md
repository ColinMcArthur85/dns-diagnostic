# Setup Checklist

## 0) Define scope + success criteria

- [x] Confirm Phase 1 scope is DNS-only (no SSL checks)
- [x] Confirm supported platforms: AttractWell (AW) + GetOiling (GO)
- [x] Confirm supported connection paths:
  - [x] Option 1: Nameserver change to LiquidWeb (managed DNS)
  - [x] Option 2: Record-level changes (A + CNAME), preserve email
- [x] Define what “done” means for Phase 1:
  - [x] Given domain + answers to intent questions → tool returns a deterministic action plan + warnings

## 1) Create the project skeleton

- [x] Create repo/folder structure (keep it simple)
  - [x] /docs (markdown rules, examples)
  - [x] /config (platform constants + provider fingerprints)
  - [x] /src (dns lookup + decision engine)
  - [x] /tests (fixtures for DNS snapshots)
- [x] Add a minimal README with run instructions

## 2) Codify platform DNS requirements (config first)

- [x] Create a versioned config object/file for platform constants
  - [x] LiquidWeb nameservers: ns.liquidweb.com, ns1.liquidweb.com
  - [x] Website record targets:
    - [x] A @ → 199.189.226.101
    - [x] CNAME www → root domain (example.com)
- [x] Encode decision options (Option 1 vs Option 2) as data (not prose)
- [x] Add a change log note for future edits (e.g., IP changes)

## 3) Define intent questions (the minimum set)

- [x] Implement these as explicit inputs (UI prompts or CLI flags):
  - [x] Has existing emails/subdomains/special DNS to keep from another provider? (yes/no)
  - [x] If email exists: is it provided by AW/GO? (yes/no)
  - [x] Wants email from AW/GO or external provider? (AW/GO/external/none)
  - [x] Comfortable editing DNS? (yes/no)
  - [x] Knows registrar? (yes/no)
  - [x] Wants us to manage DNS? (yes/no)

## 4) Implement DNS lookup (free resolver-based)

- [x] Choose resolver strategy:
  - [x] Query via public resolvers (Cloudflare 1.1.1.1 + Google 8.8.8.8) or system resolver
- [x] Implement record fetch for:
  - [x] NS
  - [x] A (root)
  - [x] CNAME (www)
  - [x] MX
  - [x] TXT
- [x] Normalize results into a consistent schema (arrays of records with host/value/ttl)
- [x] Add basic error handling:
  - [x] NXDOMAIN / no answer
  - [x] Timeout
  - [x] SERVFAIL

## 5) Build email provider detection (fingerprints)

- [x] Create a small provider fingerprint map (start with 3–5)
  - [x] Google Workspace (MX hosts like aspmx.l.google.com, etc.)
  - [x] Microsoft 365 (MX host patterns)
  - [x] Rackspace / AW email (if applicable)
  - [x] “Unknown” fallback
- [x] Detect:
  - [x] has_custom_email (MX exists)
  - [x] email_provider_detected
- [x] Parse TXT for:
  - [x] SPF (v=spf1)
  - [x] DMARC (\_dmarc)
  - [x] DKIM (selector-based; best-effort)

## 6) Implement the decision engine (deterministic)

- [x] Determine connection option:
  - [x] Option 1 if user says no external dependencies OR email is AW/GO-managed
  - [x] Option 2 if user says yes external dependencies OR third-party MX detected
- [ ] Validate current DNS against the chosen option:
  - [ ] Option 1: are nameservers already LiquidWeb?
  - [ ] Option 2: do @ and www already match required targets?
- [ ] Generate blocking issues and warnings:
  - [ ] Conflicting A/CNAME records for @ or www
  - [x] Third-party MX present → warning to not change MX
  - [ ] “User unsure / registrar unknown” → recommend delegate access

## 6.5) Handle subdomain connections (CNAME-based)

- [x] Detect whether the user is connecting a root domain or a subdomain
- [x] Define subdomain platform targets (config-driven):
  - [x] GetOiling subdomain target: sites.getoiling.com
  - [x] AttractWell subdomain target: sites.attractwell.com
- [x] Subdomain DNS rules (always record-level, never nameserver-based):
  - [x] Record type: CNAME
  - [x] Host/Name: subdomain prefix only (e.g. "blog", "members", "go")
  - [x] Value/Target:
    - [x] GetOiling → sites.getoiling.com
    - [x] AttractWell → sites.attractwell.com
- [ ] Validate existing DNS before recommending changes:
  - [ ] Check for existing CNAME on the same host
  - [ ] Check for conflicting A records on the same host
  - [ ] If conflict exists → mark as blocking issue
- [ ] Generate prescriptive guidance:
  - [ ] Do NOT change nameservers for subdomain-only connections
  - [ ] Do NOT modify MX or email-related records
  - [ ] Only add or update the required CNAME record
- [ ] Action plan output for subdomains should explicitly state:
  - [x] Full record to add (type, host, value)
  - [ ] Example using the customer’s actual subdomain
  - [ ] Expected propagation window ("within a few hours, sometimes longer")
- [ ] Delegate access recommendation:
  - [ ] If customer is unsure how to add a CNAME → recommend delegate access
  - [ ] If DNS provider is unknown → recommend delegate access

## 7) Generate the action plan (output)

- [x] Produce a structured JSON output first:
  - [x] domain
  - [x] dns_snapshot
  - [x] email_state
  - [x] intent
  - [ ] conflicts[]
  - [x] recommended_actions[]
  - [x] delegate_access_recommended
- [ ] Produce a human-readable plan second (derived from JSON):
  - [ ] Support-facing summary
  - [ ] Customer-facing instructions

## 8) Add fixtures + tests (avoid regressions)

- [ ] Create sample DNS snapshots as JSON fixtures:
  - [x] No MX, default registrar NS
  - [x] Google Workspace MX + existing SPF/DMARC
  - [ ] Cloudflare nameservers
  - [ ] Conflicting A/CNAME records
- [ ] Unit test:
  - [x] provider detection
  - [x] option selection logic
  - [ ] action plan generation

## 9) Build a minimal interface (internal first)

- [x] Start with one of:
  - [x] CLI tool (fastest)
  - [ ] Internal web page/form behind auth
- [ ] Inputs:
  - [x] domain
  - [ ] intent questions
- [x] Outputs:
  - [x] action plan + warnings
  - [ ] copy/paste blocks for DNS records

## 10) Phase 2 (later): AI explainer layer

- [ ] Use the JSON output as the only source-of-truth context
- [ ] Prompt the model to:
  - [ ] explain findings
  - [ ] present next steps
  - [ ] answer follow-ups without inventing records
- [ ] Add guardrails:
  - [ ] “If unknown, say you don’t know and recommend contacting support”
