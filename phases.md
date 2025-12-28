## Phase 1 — Deterministic Diagnostics Engine (no AI yet)

Build a rules-based domain analyzer first:

- DNS records
- SSL status
- SPF / DKIM / DMARC checks
- Registrar / nameserver mismatch detection

This becomes:

- A shared internal tool
- A future customer-facing module
- A truth source the AI can reference

> AI without a deterministic core is a hallucination engine.

## Phase 2 — AI as a translator, not a decision-maker

Once the diagnostics are solid:

- Feed the structured results to an LLM
- Ask it to explain, not infer
- Keep the AI stateless and bounded

### Example flow:

1. User enters domain
2. System runs checks → returns JSON
3. AI converts that JSON into:
   - Support-friendly explanation
   - Customer-friendly explanation
   - Suggested next steps

This matches exactly how Greg already thinks about AI.

## Phase 3 — Conversational layer (optional, later)

Only after phases 1–2:

- Add conversational memory
- Let users ask follow-ups
- Still grounded in the same deterministic data

At that point, it feels like a chatbot — without being fragile.
