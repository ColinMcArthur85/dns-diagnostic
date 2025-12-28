import argparse
import json
import sys
import os

# Add src to path if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_loader import ConfigLoader
from src.dns_lookup import DNSLookup
from src.email_detector import EmailDetector
from src.decision_engine import DecisionEngine
from src.action_plan_builder import ActionPlanBuilder
from src.ai_translator import AITranslator

def main():
    parser = argparse.ArgumentParser(description="DNS Diagnostic Tool (Phase 1)")
    parser.add_argument("--domain", required=True, help="Domain to analyze")
    parser.add_argument("--platform", required=True, choices=['attractwell', 'aw', 'getoiling', 'go'], help="Target platform")
    
    # Intent flags
    parser.add_argument("--has-external", action="store_true", dest="has_external_dependencies", help="User has external dependencies/services")
    parser.add_argument("--email-managed", action="store_true", dest="email_managed_by_platform", help="Email is managed by platform")
    parser.add_argument("--email-provided-by-platform", action="store_true", dest="email_provided_by_platform", help="Email is provided by AW/GO (only if email exists)")
    parser.add_argument("--email-choice", choices=['aw', 'go', 'external', 'none'], dest="email_choice", help="Wants email from AW/GO, external provider, or none")
    parser.add_argument("--comfortable", action="store_true", dest="comfortable_editing_dns", help="User is comfortable editing DNS")
    parser.add_argument("--registrar-known", action="store_true", dest="registrar_known", help="User knows their registrar")
    parser.add_argument("--delegate-dns", action="store_true", dest="delegate_dns_management", help="Wants us to manage DNS")
    parser.add_argument("--ai", action="store_true", help="Enable AI-generated summaries and next steps")
    parser.add_argument("--sections", nargs="+", help="Specific DNS sections or records to check (e.g. web, email, A, MX)")

    args = parser.parse_args()

    # 1. Load Config
    try:
        config = ConfigLoader()
    except Exception as e:
        print(json.dumps({"error": f"Failed to load config: {str(e)}"}))
        sys.exit(1)

    # 2. DNS Lookup
    dns_tool = DNSLookup()
    print(f"Analyzing {args.domain}...", file=sys.stderr)
    snapshot = dns_tool.get_all_records(args.domain, filter_sections=args.sections)

    # 3. Email Detection
    email_tool = EmailDetector(config.get_email_rules())
    mx_records = snapshot.get('MX', [])
    txt_records = snapshot.get('TXT', [])
    
    # If root, we use the root TXT. If subdomain, maybe different?
    # Email is usually bound to root. If checking subdomain, should we check root MX?
    # Spec says "Normalize DNS results into a consistent schema".
    # And "Email ... detection only".
    # Usually we check root for email even if setting up subdomain?
    # We will assume what we queried is what we analyze for now.
    
    email_state = email_tool.detect_provider(mx_records)
    # Enhance specific flags
    txt_analysis = email_tool.analyze_txt_records(txt_records)
    email_state.update(txt_analysis)
    
    # Analyze DMARC from dns_snapshot
    dmarc_analysis = email_tool.analyze_dns_snapshot(snapshot)
    email_state.update(dmarc_analysis)

    # Analyze DKIM from dns_snapshot
    dkim_records = snapshot.get('DKIM', [])
    dkim_analysis = email_tool.analyze_dkim(dkim_records)
    email_state.update(dkim_analysis)

    # 4. Decision Engine
    decision_engine = DecisionEngine(config)
    
    intent = {
        "has_external_dependencies": args.has_external_dependencies,
        "email_managed_by_platform": args.email_managed_by_platform,
        "email_provided_by_platform": args.email_provided_by_platform,
        "email_choice": args.email_choice,
        "comfortable_editing_dns": args.comfortable_editing_dns,
        "registrar_known": args.registrar_known,
        "delegate_dns_management": args.delegate_dns_management,
        "queried_sections": args.sections
    }
    
    decision = decision_engine.evaluate(args.domain, args.platform, intent, email_state, snapshot)

    # 5. Action Plan
    builder = ActionPlanBuilder(config)
    final_plan = builder.build_plan(decision, snapshot, email_state)

    # 6. AI Translation (Optional)
    if args.ai:
        print(f"Generating AI insights for {args.domain}...", file=sys.stderr)
        try:
            translator = AITranslator()
            ai_insights = translator.translate_diagnostic(final_plan)
            final_plan["ai_insights"] = ai_insights
        except Exception as e:
            final_plan["ai_insights"] = {"error": str(e)}

    # Output JSON
    print(json.dumps(final_plan, indent=2))

if __name__ == "__main__":
    main()
