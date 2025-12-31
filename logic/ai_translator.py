import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AITranslator:
    """Phase 2: AI as a translator, not a decision-maker.
    
    This class translates structured DNS diagnostic data into human-readable explanations.
    It follows strict guardrails to prevent hallucination and only translates existing data.
    """
    
    def __init__(self, model="gpt-5-mini"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def _get_system_prompt(self, audience="customer"):
        """Generate system prompt with strict guardrails based on audience."""
        
        base_guardrails = """
**CRITICAL GUARDRAILS - YOU MUST FOLLOW THESE STRICTLY**:
1. **NEVER invent or suggest DNS records** that are not explicitly mentioned in the provided diagnostic data
2. **ONLY translate existing data** - you are a translator, not a decision-maker
3. If you don't know something or it's not in the data, say "I don't have that information" or "Please contact support for details"
4. **DO NOT recommend specific DNS values** unless they are already in the `recommended_actions` array
5. **DO NOT diagnose issues** beyond what's in the `conflicts` and `warnings` arrays
6. Stick to facts from the JSON only
"""

        if audience == "support":
            return f"""
You are a technical DNS analysis assistant for SUPPORT STAFF.

{base_guardrails}

**Your Audience**: Internal support team members who understand DNS basics but need clear technical summaries.

**Your Task**: Translate the diagnostic JSON into a concise technical summary.
IMPORTANT CONTEXT: 
- If `connection_option` is `option_2`, we are using record-level changes. Explain that this is likely to preserve existing email or other services.
- Highlight if the A/CNAME records match despite nameservers being 'External'.

**Technical Summary Requirements**:
- Current DNS state (what's configured correctly, what's missing, what conflicts exist)
- Specific issues found (from `conflicts` and `warnings` arrays only)
- Required actions (from `recommended_actions` array only)
- Delegate access status and why it's recommended/not recommended

**Tone**: Professional, technical but clear. Use DNS terminology appropriately.

**Output Format**: JSON with these exact keys:
- "technical_summary": Brief technical overview (2-3 sentences)
- "issues": Array of specific issues found (from conflicts/warnings only, or empty array)
- "actions_required": Array of actions (from recommended_actions only, or empty array)
- "notes": Array of important context for support staff (e.g., platform-managed domain detected, email override occurred)

ONLY output valid JSON. No other text.
"""
        else:  # customer
            return f"""
You are a helpful DNS assistant explaining domain connection status to CUSTOMERS.

{base_guardrails}

**Your Audience**: Business owners who likely don't understand DNS. Be reassuring and clear.

**Your Task**: Translate the diagnostic JSON into plain English:
- Explain what we found in simple terms.
- **IMPORTANT**: If the domain is successful but nameservers are 'External', explain that their domain is correctly connected while keeping their email/other services safe where they are.
- If there are problems, explain what they mean (not just "CNAME conflict")
- If action is needed, explain it simply without technical jargon
- Use analogies if helpful (e.g., "Nameservers are like your domain's phone company")

**Tone**: Friendly, reassuring, non-technical. Avoid acronyms unless you explain them.

**Special Cases**:
- If `is_completed` is true: Start with good news!
- If `connection_option` is `option_2`: Mention that we kept their existing domain settings (nameservers) to make sure things like email don't break.
- If there are `potential_issues`: Gently mention unchecked items
- If delegate access is recommended: Explain why in simple terms

**Output Format**: JSON with these exact keys:
- "summary": Clear explanation of current status (2-4 sentences)
- "what_this_means": Plain-English explanation of any issues or next steps
- "next_steps": Array of simple action items or questions to guide them

ONLY output valid JSON. No other text.
"""

    def translate_diagnostic(self, diagnostic_json, audience="customer"):
        """
        Translates structured diagnostic JSON into human-readable explanations.
        
        Args:
            diagnostic_json: The complete diagnostic result from the engine
            audience: "customer" or "support" - determines tone and detail level
            
        Returns:
            Dictionary with translated explanations appropriate for the audience
        """
        system_prompt = self._get_system_prompt(audience)
        
        # Create a cleaned version of the JSON to send (remove sensitive internal data)
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
            "email_state": {
                "has_mx": diagnostic_json.get("email_state", {}).get("has_mx", False),
                "provider": diagnostic_json.get("email_state", {}).get("provider"),
                "display_name": diagnostic_json.get("email_state", {}).get("display_name"),
                "has_spf": diagnostic_json.get("email_state", {}).get("has_spf", False),
                "has_dmarc": diagnostic_json.get("email_state", {}).get("has_dmarc", False),
            },
            "delegate_access": diagnostic_json.get("delegate_access", {}),
            "comparison": diagnostic_json.get("comparison", [])
        }
        
        user_content = f"""Analyze this DNS diagnostic data and provide {audience}-facing explanation:

{json.dumps(clean_data, indent=2)}

Remember: Only translate what's in the data. Do not invent records or suggest actions beyond what's in recommended_actions."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"}
            )
            
            ai_result = json.loads(response.choices[0].message.content)
            
            # Add metadata about the translation
            ai_result["_metadata"] = {
                "audience": audience,
                "model": self.model,
                "guardrails_active": True
            }
            
            return ai_result
            
        except Exception as e:
            # Fail gracefully
            if audience == "support":
                return {
                    "error": f"AI translation failed: {str(e)}",
                    "technical_summary": "Error generating AI analysis.",
                    "issues": [],
                    "actions_required": [],
                    "notes": ["AI translation unavailable - refer to raw diagnostic data"]
                }
            else:
                return {
                    "error": f"AI translation failed: {str(e)}",
                    "summary": "We completed the diagnostic but couldn't generate a summary. Please review the technical details or contact support.",
                    "what_this_means": "The system is working, but the explanation service is temporarily unavailable.",
                    "next_steps": ["Contact support for help understanding these results"]
                }

    def translate_both(self, diagnostic_json):
        """Generate both support and customer translations in one call."""
        return {
            "support": self.translate_diagnostic(diagnostic_json, audience="support"),
            "customer": self.translate_diagnostic(diagnostic_json, audience="customer")
        }
