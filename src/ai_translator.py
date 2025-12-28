import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AITranslator:
    def __init__(self, model="gpt-4o"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def translate_diagnostic(self, diagnostic_json):
        """
        Takes the structured diagnostic JSON and returns three versions of explanations.
        """
        system_prompt = """
You are a helpful DNS assistant. Your job is to analyze technical DNS diagnostic data and translate it into a single, high-quality analysis for an audience that MAY NOT understand DNS at all.

**Tone & Audience**:
- Speak in plain English. Avoid jargon where possible. If you use a term like "A Record", briefly explain its purpose (e.g., "points your domain to your website hosting").
- The end user is likely a small business owner. Be helpful, reassurring, and clear.

**Priorities for the analysis**:
1. **Respect the Query Context**: If the user only asked for "Email Service", focus the primary reporting on that. If those records are perfect, start by saying so.
2. **Handle Potential Issues**: If `is_completed` is true but there are items in `potential_issues`, it means the specific records requested are fine, but other critical records (like those for web hosting) were NOT checked and are likely missing. In this case, acknowledge the success of the requested check (e.g., "Your email records are perfectly configured!") but then add a helpful note like: "We noticed you haven't checked your website hosting records yet. Would you like to verify those next to ensure your site is fully connected?"
3. **Explain Nameservers Carefully**: If nameservers are different from our target, explain that this is often OK, especially if email is already working.
4. **A and CNAME Records**: If missing or conflicting in the queried scope, explain their purpose in plain English.
5. **Handle Expired NameBright Domains**: Keep the specific TurnCommerce/NameBright phrasing for expired nameservers.
6. **Next Steps as Questions**: For `next_steps`, if the requested check is done, use questions to lead the user, e.g., "Do you need to verify your website hosting connection next?" or "Are you planning to move your email service to our platform later?"

Your output must be a JSON object with the following keys:
- summary (string: a clear, concise, beginner-friendly analysis of the current state)
- next_steps (array of strings: clear, non-technical actionable steps or "digging deeper" questions)

Do not include any other text in your response, only the raw JSON.
"""

        user_content = f"Analyze the following DNS diagnostic data and connection plan:\n\n{json.dumps(diagnostic_json, indent=2)}"

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
            return ai_result
        except Exception as e:
            return {
                "error": f"AI translation failed: {str(e)}",
                "support_summary": "Error generating summary.",
                "customer_summary": "Error generating summary.",
                "next_steps": ["Check logs and try again."]
            }
