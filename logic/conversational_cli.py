#!/usr/bin/env python3
"""
Phase 3: Conversational CLI
Allows chat-based interactions grounded in diagnostic data.
"""

import argparse
import json
import sys
from conversational_agent import ConversationalAgent

def main():
    parser = argparse.ArgumentParser(description="DNS Diagnostic Conversational Agent (Phase 3)")
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Start conversation
    start_parser = subparsers.add_parser('start', help='Start a new conversation')
    start_parser.add_argument('--diagnostic', required=True, help='Diagnostic data JSON')
    start_parser.add_argument('--audience', choices=['customer', 'support'], default='customer', help='Audience type')
    
    # Chat
    chat_parser = subparsers.add_parser('chat', help='Continue conversation')
    chat_parser.add_argument('--diagnostic', required=True, help='Diagnostic data JSON')
    chat_parser.add_argument('--history', required=True, help='Conversation history JSON')
    chat_parser.add_argument('--message', required=True, help='User message')
    chat_parser.add_argument('--audience', choices=['customer', 'support'], default='customer', help='Audience type')
    
    args = parser.parse_args()
    
    agent = ConversationalAgent()
    
    if args.command == 'start':
        diagnostic_data = json.loads(args.diagnostic)
        result = agent.start_conversation(diagnostic_data, audience=args.audience)
        print(json.dumps(result, indent=2))
        
    elif args.command == 'chat':
        diagnostic_data = json.loads(args.diagnostic)
        history = json.loads(args.history)
        result = agent.chat(diagnostic_data, history, args.message, audience=args.audience)
        print(json.dumps(result, indent=2))
        
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
