# DNS Diagnostic Tool - Complete 🎉

A three-phase DNS diagnostic and troubleshooting system with AI-powered assistance that never hallucinates.

## 🚀 All Phases Complete!

### ✅ Phase 1: Deterministic Diagnostics Engine
**The Truth Source** - Rules-based domain analyzer
- DNS record validation (A, CNAME, MX, TXT, NS, SPF, DMARC, DKIM)
- Email provider detection
- Conflict detection (CNAME/A conflicts, nameserver mismatches)
- Connection option selection (nameserver vs record-level)
- Subdomain support
- 21/21 tests passing

### ✅ Phase 2: AI as a Translator
**Bounded Explanations** - Never invents, only translates
- Dual-audience modes (Customer & Support)
- Strict guardrails prevent hallucination
- Temperature 0.3 for consistency
- Grounded in Phase 1 diagnostic data only
- Visual tab interface for switching modes

### ✅ Phase 3: Conversational Layer
**Natural Dialogue** - Ask follow-up questions
- Multi-turn conversations with memory
- Session management
- Still grounded in diagnostic data
- Beautiful chat UI
- Suggested questions
- Real-time responses

---

## 📋 Features

### Core Diagnostics
- ✅ **DNS Record Analysis**: A, CNAME, MX, TXT, NS, SPF, DMARC, DKIM
- ✅ **Email Detection**: Google Workspace, Microsoft 365, custom providers
- ✅ **Conflict Detection**: A/CNAME conflicts, nameserver mismatches
- ✅ **Subdomain Support**: Root domains and subdomains
- ✅ **WHOIS Integration**: Registrar and nameserver information
- ✅ **Action Plans**: Step-by-step DNS configuration guides
- ✅ **Copy/Paste Blocks**: Easy DNS record copying

###AI Capabilities
- ✅ **Customer Mode**: Plain English explanations
- ✅ **Support Mode**: Technical details and DNS terminology
- ✅ **Conversational Chat**: Ask follow-up questions
- ✅ **Suggested Questions**: Context-aware prompts
- ✅ **Guardrails**: Never hallucinates DNS records
- ✅ **Grounded Responses**: Only references diagnostic data

### Platforms Supported
- ✅ AttractWell
- ✅ GetOiling

---

## 🛠️ Tech Stack

### Backend (Python)
- `dnspython` - DNS lookups
- `python-whois` - WHOIS queries
- `openai` - AI translations
- `pytest` - Testing

### Frontend (Next.js)
- React 18
- TypeScript
- Tailwind CSS
- Framer Motion (animations)
- Lucide React (icons)

---

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.8+
python3 --version

# Node.js 18+
node --version

# OpenAI API Key (for AI features)
export OPENAI_API_KEY="sk-..."
```

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/dns-diagnostic.git
cd dns-diagnostic

# Install Python dependencies
pip3 install -r requirements.txt

# Install UI dependencies
cd ui
npm install
```

### Run CLI

```bash
# Basic diagnostic
python3 src/main.py --domain example.com --platform attractwell

# With AI (customer mode)
python3 src/main.py --domain example.com --platform attractwell --ai --ai-audience customer

# With AI (support mode)
python3 src/main.py --domain example.com --platform attractwell --ai --ai-audience support

# Both views
python3 src/main.py --domain example.com --platform attractwell --ai --ai-audience both

# With intent flags
python3 src/main.py --domain example.com --platform attractwell --ai \
  --has-external --comfortable --registrar-known
```

###Run Web UI

```bash
cd ui
npm run dev
# Visit http://localhost:3000
```

---

## 💡 Usage Examples

### CLI Example

```bash
$ python3 src/main.py --domain mysite.com --platform aw --ai --ai-audience customer

Analyzing mysite.com...
Generating AI insights for mysite.com (audience: customer)...

{
  "domain": "mysite.com",
  "is_completed": false,
  "recommended_actions": [
    {
      "action": "add_record",
      "type": "A",
      "host": "@",
      "value": "192.0.2.1"
    }
  ],
  "ai_insights": {
    "summary": "Your domain is almost ready! We just need to add one DNS record...",
    "what_this_means": "Think of DNS like your domain's address book...",
    "next_steps": ["Log into your domain registrar...", "Add the A record..."]
  }
}
```

### Web UI Workflow

1. **Enter Domain**: Type domain name
2. **Select Platform**: AttractWell or GetOiling
3. **Advanced Options** (optional):
   - External dependencies checkbox
   - DNS comfort level
   - AI explanation mode (Customer/Support/Both)
4. **Click Diagnose**
5. **View Results**:
   - DNS comparison table
   - Conflicts and warnings
   - Action plan with copy/paste blocks
   - AI analysis (if enabled)
6. **Chat** (Phase 3):
   - Click floating chat button
   - Ask questions about the diagnostic
   - Get grounded, helpful answers

---

## 📁 Project Structure

```
dns-diagnostic/
├── src/                          # Python backend
│   ├── main.py                   # CLI entry point
│   ├── config_loader.py          # YAML config loader
│   ├── dns_lookup.py             # DNS queries
│   ├── email_detector.py         # Email provider detection
│   ├── decision_engine.py        # Connection logic
│   ├── action_plan_builder.py    # Plan generation
│   ├── ai_translator.py          # Phase 2: AI translation
│   └── conversational_agent.py   # Phase 3: Chat
├── ui/                           # Next.js frontend
│   ├── src/app/
│   │   ├── page.tsx              # Main UI
│   │   ├── components/
│   │   │   └── ChatInterface.tsx # Phase 3 chat
│   │   └── api/
│   │       ├── diagnose/         # Diagnostic API
│   │       └── chat/             # Chat API
│   └── public/
├── tests/                        # Python tests
│   ├── test_core.py              # Unit tests
│   └── fixtures/                 # Test data
├── config/
│   └── domain_rules.yaml         # DNS configuration rules
├── PHASE_1_COMPLETE.md
├── PHASE_2_COMPLETE.md
├── PHASE_3_COMPLETE.md
└── README.md
```

---

## 🧪 Testing

```bash
# Run all tests
python3 -m pytest tests/test_core.py -v

# Run specific test
python3 -m pytest tests/test_core.py::TestCore::test_action_plan_with_conflicts -v

# Test with coverage
python3 -m pytest tests/test_core.py --cov=src --cov-report=html
```

**Current Test Status**: ✅ 21/21 passing

---

## 🎨 UI Features

### Modern Design
- Dark theme with vibrant accents
- Glassmorphism effects
- Smooth animations (Framer Motion)
- Responsive layout
- Premium aesthetics

### Interactive Elements
- Copy-to-clipboard buttons
- Collapsible advanced options
- Tabbed AI insights (Customer/Support)
- Floating chat button (Phase 3)
- Real-time chat interface

### Color Coding
- 🔵 Blue = Customer-friendly content
- 🟣 Purple = Support/technical content
- 🟢 Green = Success/completed
- 🔴 Red = Conflicts/errors
- ⚪ Gray = Information

---

## 📖 Documentation

- **[Phase 1 Details](PHASE_1_COMPLETE.md)** - Deterministic engine
- **[Phase 2 Details](PHASE_2_COMPLETE.md)** - AI translator with guardrails
- **[Phase 3 Details](PHASE_3_COMPLETE.md)** - Conversational layer
- **[Setup Checklist](setup_checklist.md)** - Implementation tracking
- **[Phases Overview](phases.md)** - Project philosophy

---

## 🔒 Security & Privacy

- **No DNS Record Invention**: AI strictly bounded to diagnostic data
- **No External Context**: AI has zero knowledge beyond the diagnostic
- **Grounded Responses**: All answers reference actual DNS records
- **Session Isolation**: Each conversation is independent
- **API Key Security**: OpenAI key stored in environment variables

---

## 🤝 Contributing

This is an internal tool. For questions or improvements:
1. Review the phase documentation
2. Check `setup_checklist.md` for implementation details
3. Run tests before submitting changes
4. Follow the established patterns (Phase 1 → 2 → 3)

---

## 📜 License

Internal use only.

---

## 🎯 Roadmap

### Phase 1 ✅
- [x] Deterministic diagnostics
- [x] DNS validation
- [x] Conflict detection
- [x] Email provider detection
- [x] Action plan generation
- [x] Copy/paste blocks

### Phase 2 ✅
- [x] AI translator
- [x] Customer mode
- [x] Support mode
- [x] Guardrails
- [x] Tabbed UI

### Phase 3 ✅
- [x] Conversational agent
- [x] Session management
- [x] Chat interface
- [x] Suggested questions
- [x] Multi-turn dialogue

### Future Enhancements 🔮
- [ ] Persistent session storage (Redis/Database)
- [ ] More platform support
- [ ] SSL/TLS validation
- [ ] Historical diagnostic tracking
- [ ] Bulk domain analysis
- [ ] Webhook notifications
- [ ] Mobile app

---

## 📊 Stats

- **Lines of Code**: ~2,500+
- **Test Coverage**: 21 tests passing
- **Phases**: 3/3 complete
- **Platforms**: 2 (AttractWell, GetOiling)
- **DNS Record Types**: 9 (A, CNAME, MX, TXT, NS, SPF, DMARC, DKIM, SOA)
- **AI Modes**: 3 (Customer, Support, Both)

---

## 🙏 Credits

Built with:
- **OpenAI GPT-4o** - AI translations and conversations
- **Next.js** - React framework
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **dnspython** - DNS lookups
- **Greg's Vision** - AI philosophy and guardrails

---

**Status**: ✅ Production Ready  
**Version**: 3.0.0 (All Phases Complete)  
**Last Updated**: December 31, 2025

**Made with ❤️ for safe, grounded AI interactions**
