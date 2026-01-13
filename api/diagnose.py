import json
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from logic.config_loader import ConfigLoader
from logic.dns_lookup import DNSLookup
from logic.email_detector import EmailDetector
from logic.decision_engine import DecisionEngine
from logic.action_plan_builder import ActionPlanBuilder
from logic.ai_translator import AITranslator

from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data) if post_data else {}

            domain = data.get('domain')
            platform = data.get('platform', 'attractwell')
            sections = data.get('sections', ['all'])
            intent_input = data.get('intent', {})
            ai_audience = data.get('ai_audience', 'customer')

            if not domain:
                self._send_json({"error": "Domain is required"}, 400)
                return

            # 1. Load Config
            config = ConfigLoader()

            # 2. DNS Lookup
            dns_tool = DNSLookup()
            snapshot = dns_tool.get_all_records(domain, filter_sections=sections)

            # 3. Email Detection
            email_tool = EmailDetector(config.get_email_rules())
            mx_records = snapshot.get('MX', [])
            txt_records = snapshot.get('TXT', [])
            
            email_state = email_tool.detect_provider(mx_records)
            email_state.update(email_tool.analyze_txt_records(txt_records))
            email_state.update(email_tool.analyze_dns_snapshot(snapshot))
            
            dkim_records = snapshot.get('DKIM', [])
            email_state.update(email_tool.analyze_dkim(dkim_records))

            # 4. Decision Engine
            decision_engine = DecisionEngine(config)
            
            intent = {
                "has_external_dependencies": intent_input.get('has_external_dependencies', False),
                "email_managed_by_platform": intent_input.get('email_managed_by_platform', False),
                "comfortable_editing_dns": intent_input.get('comfortable_editing_dns', True),
                "registrar_known": intent_input.get('registrar_known', True),
                "delegate_dns_management": intent_input.get('delegate_dns_management', False),
                "queried_sections": sections
            }
            
            decision = decision_engine.evaluate(domain, platform, intent, email_state, snapshot)

            # 5. Action Plan
            builder = ActionPlanBuilder(config)
            final_plan = builder.build_plan(decision, snapshot, email_state)

            # 6. AI Translation
            use_ai = data.get('use_ai', True)
            if use_ai:
                try:
                    translator = AITranslator()
                    if ai_audience == 'both':
                        ai_insights = translator.translate_both(final_plan)
                    else:
                        ai_insights = translator.translate_diagnostic(final_plan, audience=ai_audience)
                    final_plan["ai_insights"] = ai_insights
                except Exception as ai_error:
                    final_plan["ai_insights"] = {"error": str(ai_error)}
            else:
                final_plan["ai_insights"] = None

            self._send_json(final_plan, 200)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _send_json(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
