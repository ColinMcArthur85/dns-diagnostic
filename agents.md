# Agent Framework: DNS Diagnostic Tool

This document serves as a guide for AI agents and developers working on the DNS Diagnostic Tool. It outlines the project structure, development workflows, and coding standards.

## 1. Project Overview
A hybrid application designed to diagnose DNS configurations and provide guided setup plans for AttractWell and GetOiling platforms.

- **Frontend**: Next.js (TypeScript, Tailwind CSS, Framer Motion) located in `/ui`.
- **Backend**: Python CLI engine in `/src` for deterministic diagnostics and AI-driven insights.
- **Integration**: The UI calls the Python engine via a Node.js `child_process` execution in a Next.js API route.
- **Truth Source**: All platform logic and DNS rules are stored in `domain_rules.yaml`.
- **Core Philosophy**: 
  - **Phase 1 (Deterministic Core)**: All diagnostic decisions must be rules-based and driven by `domain_rules.yaml`.
  - **Phase 2 (AI Translation)**: Use AI to translate structured JSON results into human-friendly explanations. AI is a *translator*, not a *decision-maker*. Never let AI infer DNS records or connection paths; it must only report what the engine found.

## 2. Build and Test Commands

### Backend (Python)
- **Environment**: Use a virtual environment (`python3 -m venv .venv`).
- **Install Dependencies**: `pip install -r requirements.txt`
- **CLI Usage**: 
  ```bash
  python3 src/main.py --domain example.com --platform attractwell --ai
  ```
- **Testing**: Run `pytest` to execute backend unit tests.

### Frontend (Next.js)
- **Directory**: `cd ui`
- **Install Dependencies**: `npm install`
- **Development**: `npm run dev` (runs on [http://localhost:3000](http://localhost:3000))
- **Build**: `npm run build`
- **Lint**: `npm run lint`

## 3. Code Style Guidelines

- **Minimal Commenting**: Do not include comments unless they are 100% required to explain a super complex block of code. Code should be self-documenting through clear naming and structure.

### Python (Backend)
- **Modularization**: Keep logic isolated. Use `dns_lookup.py` for queries, `decision_engine.py` for logic, and `action_plan_builder.py` for formatting output.
- **Execution Flow**: `main.py` is the entry point. It must output valid JSON to `stdout` and any diagnostic logs/errors to `stderr`.
- **Config-Driven**: Never hardcode platform-specific DNS records. Fetch them from `ConfigLoader`.

### TypeScript/React (Frontend)
- **Visuals**: Maintain the "Antigravity" dark theme. Use `framer-motion` for entry animations and transitions.
- **CSS Strategy**: 
  - Use Tailwind for utility spacing and layout.
  - Use semantic classes in `globals.css` for complex components (e.g., `.stat-card`, `.info-panel`, `.action-item`).
- **State Management**: Use React `useState` and `useEffect` for local UI state. API calls should handle loading/error states gracefully.

## 4. Testing Instructions
- **Validating Logic**: When changing `domain_rules.yaml` or the `DecisionEngine`, update or add test cases in `tests/test_core.py`.
- **Mocking**: Use the fixtures in `tests/fixtures/` to simulate DNS snapshots without making live network calls.
- **UI Verification**: Ensure the "Action Plan" and "AI Insights" sections render correctly for various scenarios (e.g., missing A record, conflicting MX records).

## 5. Security Considerations
- **Environment Secrets**: `OPENAI_API_KEY` must be stored in `.env` and never logged or exposed to the frontend browser directly.
- **Shell Safety**: The `exec` call in `ui/src/app/api/diagnose/route.ts` uses user-provided domain strings. While simple, ensure domain validation is performed to prevent unexpected shell behavior.
- **Data Privacy**: Do not store or log WHOIS results or DNS snapshots beyond the immediate request/response cycle.
- **Injection Safety**: The `exec` call in `ui/src/app/api/diagnose/route.ts` uses user-provided domain strings. While simple, ensure domain validation is performed to prevent unexpected shell behavior. 