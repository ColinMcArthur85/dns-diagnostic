# DNS Diagnostic App 🛠️

A specialized internal tool built to automate DNS health checks for AttractWell/GetOiling support tickets. This app reduces manual WHOIS/Dig lookups by surfacing misconfigurations in a single view.

## 🏗️ Technical Stack
- **Frontend**: Next.js (TypeScript, Tailwind CSS, Framer Motion)
- **Backend**: Python CLI engine for deterministic diagnostics and AI-driven insights.
- **Integration**: The UI calls the Python engine via a Node.js `child_process` execution.
- **Truth Source**: All platform logic and DNS rules are stored in `domain_rules.yaml`.

## 🚀 Systems Thinking: Why this exists
Support engineers spend ~15% of their time manually diagnosing DNS "parking" issues. This tool creates a repeatable diagnostic path, lowering the barrier to entry for junior staff and reducing escalation volume to senior TPMs.

## 📖 Related Documentation
- See [playbook.md](./playbook.md) for the Support Team's operational guide.
- See [agents.md](./agents.md) for AI and developer technical guidelines.

## 🛠️ Setup & Contribution

### Backend Setup
1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables:
   - Create a `.env` file with `OPENAI_API_KEY=your_key_here`

### Frontend Setup
1. Navigate to the UI directory:
   ```bash
   cd ui
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

### Running Tests
To run the backend unit tests:
```bash
pytest
```
