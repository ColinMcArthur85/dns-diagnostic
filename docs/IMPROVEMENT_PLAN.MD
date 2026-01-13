# DNS Diagnostic Tool - Completion Roadmap & Implementation Plan

> **Last Updated:** 2026-01-12  
> **Status:** 🚧 In Progress  
> **Owner:** Colin McArthur  

This document outlines step-by-step instructions to upgrade the DNS Diagnostic tool from a prototype to a senior-grade production utility. Each item has a checkbox `[ ]` for tracking progress.

---

## Table of Contents

- [Phase 1: Harden the DNS Logic](#phase-1-harden-the-dns-logic-the-builder-energy-lane)
- [Phase 2: Fix the AI Context](#phase-2-fix-the-ai-context-the-context-lane)
- [Phase 3: Trace Functionality](#phase-3-trace-functionality-the-senior-logic-lane)
- [Phase 4: Team Enablement](#phase-4-team-enablement-the-leverage-lane)
- [Execution Order](#execution-order)

---

## Phase 1: Harden the DNS Logic (The "Builder Energy" Lane)

**Goal:** Catch "silent killers" like IPv6 conflicts and ensure we aren't just checking for presence of good records, but **absence of bad ones**.

---

### 1.1 Update `domain_rules.yaml` — Add Global Conflict Rules

We need to explicitly define what record types conflict with each other.

**File:** `domain_rules.yaml`

#### Tasks:

- [x] **1.1.1** Add `global_conflicts` section at root level (before `platforms`)
- [x] **1.1.2** Define A record conflicts (CNAME is incompatible)
- [x] **1.1.3** Define CNAME record conflicts (A, AAAA, TXT, MX are incompatible per RFC)
- [x] **1.1.4** Add `ipv6_supported: false` flag to AttractWell and GetOiling platforms
- [x] **1.1.5** Validate YAML syntax after changes

**Code to add at root level (before `platforms:`):**

```yaml
# --- GLOBAL CONFLICT RULES ---
# Defines which record types are mutually exclusive at the same host
global_conflicts:
  # If we want an A record, these types at the same host are fatal
  A:
    - CNAME
  # If we want a CNAME, these types at the same host are fatal  
  CNAME:
    - A
    - AAAA
    - TXT   # RFC violation at root, though sometimes ignored by providers
    - MX    # RFC violation at root

# --- IPv6 PLATFORM SUPPORT ---
# Platforms that do NOT support IPv6 (AAAA records must be removed)
ipv6_unsupported_platforms:
  - attractwell
  - getoiling
```

---

### 1.2 Patch `logic/dns_lookup.py` — Add AAAA (IPv6) Record Support

We must query for IPv6 records because they often override IPv4 on modern devices/networks.

**File:** `logic/dns_lookup.py`

#### Tasks:

- [x] **1.2.1** Add `'AAAA'` to the `all_types` list in `get_all_records()` (line ~309)
- [x] **1.2.2** Add `'AAAA'` to the `'web'` section in the `mapping` dictionary (line ~314)
- [x] **1.2.3** Add `'AAAA'` to the `filter_sections` handling for `'all'` (line ~322)
- [x] **1.2.4** Add root AAAA lookup alongside A records (after line ~340)
- [x] **1.2.5** Add www AAAA lookup in the www section (after line ~351)
- [x] **1.2.6** Test AAAA lookups work correctly for a known IPv6 domain

**Code changes in `get_all_records()` method:**

```python
# Line ~309: Update all_types to include AAAA
all_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS']

# Line ~314: Update mapping to include AAAA in web
mapping = {
    'web': ['A', 'AAAA', 'CNAME', 'NS'],  # Added AAAA
    'email': ['MX', 'TXT', 'DMARC', 'DKIM'],
    'SPF': ['TXT']
}

# Line ~340: Add AAAA lookup (after the A record lookup)
# This happens automatically since AAAA is in all_types

# Line ~351: Add WWW_AAAA lookup
if check_www and not domain.startswith('www.'):
    is_web_requested = any(t in requested_types for t in ['A', 'AAAA', 'CNAME'])
    if is_web_requested:
        www_domain = f"www.{domain}"
        www_records = self.get_records(www_domain, 'CNAME')
        www_a_records = self.get_records(www_domain, 'A')
        www_aaaa_records = self.get_records(www_domain, 'AAAA')  # NEW
        
        results['WWW_CNAME'] = www_records
        results['WWW_A'] = www_a_records
        results['WWW_AAAA'] = www_aaaa_records  # NEW
```

---

### 1.3 Detect "Extra" Records in `logic/action_plan_builder.py`

We need to flag AAAA records as **high-severity conflicts** if the platform doesn't support them (which AttractWell/GetOiling do NOT).

**File:** `logic/action_plan_builder.py`

#### Tasks:

- [x] **1.3.1** Add IPv6 check at the start of `_build_comparison()` method
- [x] **1.3.2** Add AAAA records to comparison table with "conflict" status
- [x] **1.3.3** Inject AAAA conflict into `decision['conflicts']` list
- [x] **1.3.4** Add conflict for www AAAA records as well
- [x] **1.3.5** Add `delete_record` action to `recommended_actions` for AAAA removal
- [x] **1.3.6** Update `_was_record_queried()` to handle AAAA type

**Code to add in `_build_comparison()` (after Nameservers section, before line ~65):**

```python
# [NEW] Check for Rogue AAAA (IPv6) records
# Platforms like AW/GO are IPv4 only - AAAA records can block SSL generation
current_aaaa = dns_snapshot.get('AAAA', [])
www_aaaa = dns_snapshot.get('WWW_AAAA', [])
all_aaaa = current_aaaa + www_aaaa

if all_aaaa:
    aaaa_values = ", ".join([r.get('value', 'unknown') for r in all_aaaa])
    
    # Add to visual comparison
    comparison.append({
        "label": "AAAA (IPv6) Records",
        "current": aaaa_values,
        "target": "None (Delete these)",
        "status": "conflict",
        "is_required": True,
        "notes": "IPv6 records often block SSL generation on this platform and must be removed."
    })
    
    # Inject into main conflicts list
    ipv6_conflict = {
        "type": "extra_record",
        "severity": "high",
        "message": "IPv6 (AAAA) records detected. These often block SSL generation and must be deleted.",
        "blocking": True,
        "conflicting_records": all_aaaa
    }
    
    # Avoid duplicates
    existing_aaaa_conflict = any(
        c.get('type') == 'extra_record' and 'AAAA' in c.get('message', '') 
        for c in decision.get('conflicts', [])
    )
    if not existing_aaaa_conflict:
        decision.setdefault('conflicts', []).append(ipv6_conflict)
```

**Code to add in `build_plan()` for recommended actions (around line ~285):**

```python
# [NEW] Add delete actions for AAAA records
current_aaaa = dns_snapshot.get('AAAA', [])
www_aaaa = dns_snapshot.get('WWW_AAAA', [])

for aaaa_record in current_aaaa:
    actions.append({
        "action": "delete_record",
        "type": "AAAA",
        "host": "@",
        "value": aaaa_record.get('value'),
        "reason": "IPv6 records block SSL generation on this platform"
    })

for aaaa_record in www_aaaa:
    actions.append({
        "action": "delete_record",
        "type": "AAAA",
        "host": "www",
        "value": aaaa_record.get('value'),
        "reason": "IPv6 records block SSL generation on this platform"
    })
```

---

### 1.4 Load Global Conflicts in `logic/config_loader.py`

The `ConfigLoader` needs a method to retrieve the new global conflict rules.

**File:** `logic/config_loader.py`

#### Tasks:

- [x] **1.4.1** Add `get_global_conflicts()` method
- [x] **1.4.2** Add `is_ipv6_supported(platform)` method
- [x] **1.4.3** Test config loader returns correct conflict data

**Code to add:**

```python
def get_global_conflicts(self) -> dict:
    """Returns the global conflict rules for DNS record types."""
    return self.config.get('global_conflicts', {})

def is_ipv6_supported(self, platform: str) -> bool:
    """Check if a platform supports IPv6 (AAAA) records."""
    unsupported = self.config.get('ipv6_unsupported_platforms', [])
    return platform.lower() not in unsupported
```

---

## Phase 2: Fix the AI Context (The "Context" Lane)

**Goal:** Stop the AI from saying "I don't know" when the data is right there. We need to **stop over-sanitizing** the useful DNS snapshot data.

---

### 2.1 Pass Full DNS Snapshot in `logic/ai_translator.py`

The `clean_data` dictionary is stripping too much context. We need to let the AI see the raw snapshot.

**File:** `logic/ai_translator.py`

#### Tasks:

- [x] **2.1.1** Add `dns_snapshot` to the `clean_data` dictionary in `translate_diagnostic()` (line ~109-129)
- [x] **2.1.2** Add structured summary of actual DNS records (not just email_state)
- [x] **2.1.3** Update system prompts to explain how to use `dns_snapshot`
- [x] **2.1.4** Test AI can now answer "What is my SPF record?" correctly

**Code change in `translate_diagnostic()` method (around line 109):**

```python
# Create a cleaned version of the JSON to send (with full DNS context)
clean_data = {
    "domain": diagnostic_json.get("domain"),
    "platform": diagnostic_json.get("platform"),
    "is_subdomain": diagnostic_json.get("is_subdomain"),
    "connection_option": diagnostic_json.get("connection_option"),
    "is_completed": diagnostic_json.get("is_completed"),
    "status_message": diagnostic_json.get("status_message"),
    "warnings": diagnostic_json.get("warnings", []),
    "conflicts": diagnostic_json.get("conflicts", []),
    "recommended_actions": diagnostic_json.get("recommended_actions", []),
    "potential_issues": diagnostic_json.get("potential_issues", []),
    "email_state": diagnostic_json.get("email_state", {}),  # FULL email_state now
    "delegate_access": diagnostic_json.get("delegate_access", {}),
    "comparison": diagnostic_json.get("comparison", []),
    
    # [NEW] Pass the raw snapshot so AI can answer "What is my X record?"
    "dns_snapshot": diagnostic_json.get("dns_snapshot", {})
}
```

---

### 2.2 Update System Prompts to Reference DNS Snapshot

Teach the AI **how to use** the new `dns_snapshot` data.

**File:** `logic/ai_translator.py`

#### Tasks:

- [x] **2.2.1** Update `base_guardrails` to mention `dns_snapshot` as data source
- [x] **2.2.2** Add instructions for answering "What is my X record?" questions
- [x] **2.2.3** Update customer prompt special cases
- [x] **2.2.4** Update support prompt output format

**Add to `base_guardrails` (around line 25):**

```python
base_guardrails = """
**CRITICAL GUARDRAILS - YOU MUST FOLLOW THESE STRICTLY**:
1. **NEVER invent or suggest DNS records** that are not explicitly mentioned in the provided data
2. **ONLY translate existing data** - you are a translator, not a decision-maker
3. **HOW TO ANSWER "What is my X record?"**:
   - LOOK IN `dns_snapshot` for the actual records
   - Example: SPF record is in dns_snapshot.TXT (look for v=spf1)
   - Example: MX records are in dns_snapshot.MX
   - Example: A records are in dns_snapshot.A
   - If the record exists in dns_snapshot, QUOTE IT. Do NOT say "I don't know"
4. **DO NOT recommend specific DNS values** unless they are in `recommended_actions`
5. **DO NOT diagnose issues** beyond what's in `conflicts` and `warnings`
6. Stick to facts from the JSON only
"""
```

---

### 2.3 Update Conversational Agent System Prompt

The conversational agent also needs to know how to use dns_snapshot.

**File:** `logic/conversational_agent.py`

#### Tasks:

- [x] **2.3.1** Update `_get_system_prompt()` to explain dns_snapshot usage (line ~24-53)
- [x] **2.3.2** Add examples of how to find specific record types
- [x] **2.3.3** Update knowledge bounds to be more permissive about data in snapshot
- [x] **2.3.4** Test conversational agent can answer record-specific questions

**Update `_get_system_prompt()` (around line 30):**

```python
base_context = f"""
You are a helpful DNS assistant having a conversation about domain connection diagnostics.

**CRITICAL - HOW TO USE THE DATA**:
The diagnostic data below contains everything you know. Here's how to find things:

1. **`dns_snapshot`** - Contains the RAW DNS records we found:
   - `dns_snapshot.A` = A records (IPv4 addresses)
   - `dns_snapshot.AAAA` = AAAA records (IPv6 addresses)  
   - `dns_snapshot.CNAME` = CNAME records (aliases)
   - `dns_snapshot.MX` = Email server records
   - `dns_snapshot.TXT` = Text records (includes SPF)
   - `dns_snapshot.DMARC` = DMARC policy record
   - `dns_snapshot.DKIM` = DKIM signing records
   - `dns_snapshot.NS` = Nameserver records
   - `dns_snapshot.WHOIS` = Domain registration info
   
   👉 **IF USER ASKS "What is my SPF/MX/A record?", LOOK HERE FIRST!**
   
2. **`comparison`** - Shows Current vs Target for each record type
   - Use this to explain WHY a record is marked as "conflict" or "missing"
   
3. **`recommended_actions`** - The specific fixes required
   - Only recommend actions from this list
   
4. **`email_state`** - Detected email provider and configuration
   - has_mx, has_spf, has_dmarc, has_dkim status
   - provider name (Google Workspace, Microsoft 365, etc.)

**RULES**:
1. **STAY GROUNDED**: Only answer questions about what's IN the diagnostic data
2. **QUOTE ACTUAL VALUES**: When user asks about a record, quote the actual value from dns_snapshot
3. **NO NEW RECOMMENDATIONS**: Don't suggest actions beyond what's in recommended_actions
4. **SAY "I DON'T KNOW"** only if the data truly isn't in the snapshot
5. **REFER TO REPORT**: Reference specific parts of the diagnostic data

**THE DIAGNOSTIC DATA**:
{json.dumps(diagnostic_data, indent=2)}

**END OF YOUR KNOWLEDGE**
"""
```

---

## Phase 3: Trace Functionality (The "Senior Logic" Lane)

**Goal:** Bypass Cloudflare/Google public DNS caching to see if a change **just happened**.

---

### 3.1 Add Authoritative Lookup Methods to `logic/dns_lookup.py`

**File:** `logic/dns_lookup.py`

#### Tasks:

- [x] **3.1.1** Add `get_authoritative_nameservers()` method
- [x] **3.1.2** Add `bypass_cache_lookup()` method
- [x] **3.1.3** Add `trace_record()` method for comparing cached vs authoritative
- [x] **3.1.4** Add proper error handling for auth NS resolution failures
- [x] **3.1.5** Test with a domain where you just made a change

**Code to add to `DNSLookup` class:**

```python
def get_authoritative_nameservers(self, domain: str) -> List[str]:
    """
    Find the authoritative nameservers for the domain.
    
    Returns:
        List of authoritative nameserver hostnames
    """
    if not self._is_valid_domain(domain):
        return []
    if self._is_blocked_domain(domain):
        return []
        
    try:
        answers = self.resolver.resolve(domain, 'NS')
        return [str(r.target).rstrip('.') for r in answers]
    except Exception as e:
        logger.warning(f"Could not find authoritative NS for {domain}: {e}")
        return []

def bypass_cache_lookup(self, domain: str, record_type: str) -> List[Dict[str, Any]]:
    """
    Query the authoritative nameservers directly, bypassing public resolver cache.
    
    Useful for 'I just fixed it!' scenarios where users want to verify changes
    before DNS propagation completes.
    
    Args:
        domain: Domain to query
        record_type: DNS record type (A, CNAME, MX, etc.)
        
    Returns:
        List of records from authoritative source, or error dict
    """
    # Security validation
    if not self._is_valid_domain(domain):
        return [{"error": "Invalid domain format", "type": record_type}]
    if self._is_blocked_domain(domain):
        return [{"error": "Domain not allowed", "type": record_type}]
    
    auth_ns_list = self.get_authoritative_nameservers(domain)
    if not auth_ns_list:
        return [{"error": "Could not find authoritative nameservers", "type": record_type}]

    # Create a temporary resolver pointing to the auth NS
    custom_resolver = dns.resolver.Resolver()
    custom_resolver.timeout = self.DEFAULT_TIMEOUT
    custom_resolver.lifetime = self.DEFAULT_LIFETIME
    
    try:
        # Resolve the IP of the first auth NS (we need an IP, not a hostname)
        ns_ip_answers = self.resolver.resolve(auth_ns_list[0], 'A')
        ns_ip = str(ns_ip_answers[0])
        custom_resolver.nameservers = [ns_ip]
        
        # Now query using this resolver
        answers = custom_resolver.resolve(domain, record_type)
        results = []
        
        for rdata in answers:
            results.append({
                'type': record_type,
                'host': domain,
                'value': rdata.to_text().strip('"'),
                'ttl': answers.ttl,
                'source': 'authoritative',
                'nameserver': auth_ns_list[0]
            })
        return results
        
    except dns.resolver.NXDOMAIN:
        return [{"error": "Domain does not exist", "type": record_type, "source": "authoritative"}]
    except dns.resolver.NoAnswer:
        return []  # Record type doesn't exist
    except Exception as e:
        logger.warning(f"Authoritative lookup failed for {domain}/{record_type}: {e}")
        return [{"error": f"Direct lookup failed: {self._sanitize_error(e)}", "type": record_type}]

def trace_record(self, domain: str, record_type: str) -> Dict[str, Any]:
    """
    Compare cached (public resolver) vs authoritative (direct) DNS records.
    
    Useful for diagnosing propagation issues.
    
    Returns:
        {
            "cached": [...],      # What public resolvers see
            "authoritative": [...], # What the actual DNS servers have
            "propagated": bool,   # Whether they match
            "ttl_remaining": int  # Seconds until cache expires (estimate)
        }
    """
    cached = self.get_records(domain, record_type)
    authoritative = self.bypass_cache_lookup(domain, record_type)
    
    # Compare values (ignore TTL for matching)
    cached_values = set(r.get('value', '') for r in cached if not r.get('error'))
    auth_values = set(r.get('value', '') for r in authoritative if not r.get('error'))
    
    propagated = cached_values == auth_values
    
    # Estimate TTL remaining
    ttl_remaining = 0
    if cached and not cached[0].get('error'):
        ttl_remaining = cached[0].get('ttl', 0)
    
    return {
        "domain": domain,
        "record_type": record_type,
        "cached": cached,
        "authoritative": authoritative,
        "propagated": propagated,
        "ttl_remaining": ttl_remaining,
        "message": "Records match" if propagated else f"Propagation in progress (~{ttl_remaining}s remaining)"
    }
```

---

### 3.2 Add Trace API Endpoint

**File:** `src/app/api/trace/route.ts` (NEW FILE)

#### Tasks:

- [x] **3.2.1** Create new `src/app/api/trace/route.ts` file
- [x] **3.2.2** Implement POST handler calling `trace_record()` method
- [x] **3.2.3** Add request validation for domain and record_type
- [x] **3.2.4** Test API endpoint returns cached vs authoritative comparison

---

### 3.3 Add "Deep Check" UI Button (Optional/Future)

**Files:** Frontend components (TBD)

#### Tasks:

- [ ] **3.3.1** Add "Verify Recent Change" or "Deep Check" button to results view *(Optional - Frontend)*
- [ ] **3.3.2** Add loading state for trace operation *(Optional - Frontend)*
- [ ] **3.3.3** Display propagation status to user *(Optional - Frontend)*
- [ ] **3.3.4** Show helpful message about DNS propagation timing *(Optional - Frontend)*

---

## Phase 4: Team Enablement (The "Leverage" Lane)

**Goal:** Give the support team **copy-pasteable answers** and email templates.

---

### 4.1 Generate Client Email Draft in `logic/ai_translator.py`

**File:** `logic/ai_translator.py`

#### Tasks:

- [x] **4.1.1** Update support prompt to request `client_email_draft` in output
- [x] **4.1.2** Add email template structure to prompt
- [x] **4.1.3** Include placeholder for customer name `[Name]`
- [x] **4.1.4** Keep email concise and action-focused
- [x] **4.1.5** Test generated emails are professional and accurate

**Update support prompt output format (around line 56):**

```python
**Output Format**: JSON with these exact keys:
- "technical_summary": Brief technical overview (2-3 sentences)
- "issues": Array of specific issues found (from conflicts/warnings only, or empty array)
- "actions_required": Array of actions (from recommended_actions only, or empty array)
- "notes": Array of important context for support staff
- "client_email_draft": A polite, pre-written email to send to the customer. Structure:
  ```
  Hi [Name],

  I've checked your domain [domain] and here's what I found:

  [Status summary - good news first if applicable]

  [If actions needed:]
  Here's exactly what needs to be done:
  • [Action 1]
  • [Action 2]
  
  [If no actions needed:]
  Everything looks good! No changes are required.

  Let me know when this is complete, or if you have any questions!

  Best,
  [Support Team]
  ```
```

---

### 4.2 Add Copy-to-Clipboard Functionality

**Files:** Frontend components (TBD)

#### Tasks:

- [x] **4.2.1** Add "Copy Email" button next to client_email_draft
- [x] **4.2.2** Add "Copy Technical Summary" button for support view
- [x] **4.2.3** Add toast notification confirming copy success
- [x] **4.2.4** Ensure formatting is preserved when pasting

---

### 4.3 Verify API Response Includes All New Fields

**File:** `src/app/api/diagnose/route.ts`

#### Tasks:

- [x] **4.3.1** Verify `dns_snapshot` is included in API response
- [x] **4.3.2** Verify `client_email_draft` is included in `ai_insights.support`
- [x] **4.3.3** Verify AAAA records are included in snapshot
- [x] **4.3.4** Test full response structure with sample domain

---

## Execution Order

Follow this order to ensure dependencies are met:

### Batch 1: Data Foundation (Phase 1)
> *Without correct data, the AI explains wrong information*

1. [x] **Step 1.1** - Update `domain_rules.yaml` with global conflicts
2. [x] **Step 1.4** - Update `config_loader.py` to read new rules
3. [x] **Step 1.2** - Patch `dns_lookup.py` for AAAA support
4. [x] **Step 1.3** - Patch `action_plan_builder.py` for AAAA detection

### Batch 2: AI Context (Phase 2)
> *Now the AI can see the improved data*

5. [x] **Step 2.1** - Pass full dns_snapshot to AI translator
6. [x] **Step 2.2** - Update AI translator system prompts
7. [x] **Step 2.3** - Update conversational agent prompts

### Batch 3: Advanced Features (Phase 3)
> *Add as feature flag or "Deep Check" button*

8. [x] **Step 3.1** - Add authoritative lookup methods
9. [x] **Step 3.2** - Add trace API endpoint
10. [ ] **Step 3.3** - Add UI button *(Optional - Frontend)*

### Batch 4: Team Delight (Phase 4)
> *Polish and team enablement*

11. [x] **Step 4.1** - Add client email draft to AI output
12. [x] **Step 4.2** - Add copy-to-clipboard UI
13. [x] **Step 4.3** - Verify full API response structure

---

## Testing Checklist

After each batch, verify:

- [x] `npm run dev` starts without errors
- [x] Python imports work: `python3 -c "from logic.dns_lookup import DNSLookup; print('OK')"`
- [x] API responds correctly: `curl -X POST http://localhost:3000/api/diagnose -H "Content-Type: application/json" -d '{"domain": "example.com", "use_ai": false}'`
- [x] AAAA records appear in dns_snapshot (test with IPv6-enabled domain)
- [x] AI can answer "What is my SPF record?" with actual value
- [x] No regressions in existing functionality

---

## Notes

- **IPv6 Domains to Test:** `cloudflare.com`, `google.com`, `facebook.com` all have AAAA records
- **Safe Test Domains:** `example.com`, `test.com` for non-destructive testing
- **API Key Required:** OpenAI API key must be in `.env` for AI features
- **Virtual Environment:** All Python must run from `.venv/bin/python3`

---

## Bug Fixes Applied

- [x] Fixed `/api/chat` route - corrected parameter names to match `ConversationalAgent.chat()` method signature
- [x] Added venv Python path to all API routes for dependency resolution