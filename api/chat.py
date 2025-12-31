import json
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from logic.conversational_agent import ConversationalAgent

from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data) if post_data else {}

            session_id = data.get('session_id')
            message = data.get('message')
            diagnostic_data = data.get('diagnostic_data')
            audience = data.get('audience', 'customer')
            action = data.get('action', 'chat')

            agent = ConversationalAgent()
            
            if action == 'start' or not session_id:
                result = agent.start_conversation(diagnostic_data, audience=audience)
            else:
                result = agent.chat(session_id, message, diagnostic_data, audience=audience)

            self._send_json(result, 200)

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
