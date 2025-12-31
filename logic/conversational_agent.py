import os
import json
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ConversationalAgent:
    """Phase 3: Conversational layer with memory.
    
    This class adds conversational capabilities on top of Phase 1 (deterministic) 
    and Phase 2 (bounded translation). It allows follow-up questions while staying
    grounded in the original diagnostic data.
    """
    
    def __init__(self, model="gpt-4o-mini"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        
    def _get_system_prompt(self, diagnostic_data: dict, audience: str = "customer") -> str:
        """Generate system prompt that grounds conversation in diagnostic data."""
        
        base_context = f"""
You are a helpful DNS assistant having a conversation about domain connection diagnostics.

**CRITICAL - YOUR KNOWLEDGE BOUNDS**:
You have access to ONE diagnostic report for the domain "{diagnostic_data.get('domain', 'unknown')}".
This report is the ONLY source of truth you can reference. It contains:
- DNS records (current state)
- Recommended actions
- Conflicts and warnings
- Email configuration
- Connection status

**RULES YOU MUST FOLLOW**:
1. **STAY GROUNDED**: Only answer questions about what's IN the diagnostic data
2. **NO EXTERNAL KNOWLEDGE**: Don't reference other DNS concepts not in the report
3. **NO NEW RECOMMENDATIONS**: Don't suggest actions beyond what's in recommended_actions
4. **SAY "I DON'T KNOW"**: If asked about something not in the data, be honest
5. **REFER TO REPORT**: Frequently reference specific parts of the diagnostic data
6. **NO HALLUCINATION**: Never invent DNS records, values, or technical details

**THE DIAGNOSTIC DATA**:
{json.dumps(diagnostic_data, indent=2)}

**END OF YOUR KNOWLEDGE**
Everything you know is above. If a question goes beyond this data, say:
"That's not covered in this diagnostic report. Would you like me to explain what I can see, or would you prefer to run a new diagnostic?"
"""

        if audience == "support":
            return base_context + """
**YOUR AUDIENCE**: Internal support staff (technical)
**YOUR TONE**: Professional, technical, use DNS terminology
**YOUR GOAL**: Help support staff understand the diagnostic quickly and answer their technical questions
"""
        else:  # customer
            return base_context + """
**YOUR AUDIENCE**: Business owners (likely non-technical)
**YOUR TONE**: Friendly, patient, use plain English
**YOUR GOAL**: Help them understand what's happening with their domain and what they need to do next

Avoid jargon. If you must use technical terms, explain them simply.
"""

    def chat(
        self, 
        diagnostic_data: dict, 
        conversation_history: List[Dict[str, str]], 
        user_message: str,
        audience: str = "customer"
    ) -> dict:
        """
        Handle a conversational turn grounded in diagnostic data.
        
        Args:
            diagnostic_data: The original Phase 1 diagnostic output (source of truth)
            conversation_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
            user_message: The new user message
            audience: "customer" or "support"
            
        Returns:
            {
                "message": str,  # AI's response
                "grounded": bool,  # Whether response stayed within bounds
                "references": []  # Parts of diagnostic data referenced
            }
        """
        
        system_prompt = self._get_system_prompt(diagnostic_data, audience)
        
        # Build full conversation
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.4,
                max_tokens=500
            )
            
            ai_message = response.choices[0].message.content
            
            # Simple check: did AI stay grounded?
            # If it says "not in the report" or "I don't have", it's being honest
            grounded = True
            if "don't have" in ai_message.lower() or "not in" in ai_message.lower():
                grounded = "partial"  # AI admitted knowledge gap
            
            return {
                "message": ai_message,
                "grounded": grounded,
                "conversation_turn": len(conversation_history) // 2 + 1,
                "_metadata": {
                    "model": self.model,
                    "audience": audience,
                    "phase": 3
                }
            }
            
        except Exception as e:
            return {
                "message": f"I apologize, I'm having trouble processing that question. Error: {str(e)}",
                "grounded": False,
                "error": str(e)
            }

    def start_conversation(self, diagnostic_data: dict, audience: str = "customer") -> dict:
        """
        Start a new conversation with an opening message based on the diagnostic.
        
        Returns:
            {
                "opening_message": str,
                "suggested_questions": List[str]
            }
        """
        
        # Determine appropriate opening based on status
        is_completed = diagnostic_data.get('is_completed', False)
        has_conflicts = len(diagnostic_data.get('conflicts', [])) > 0
        has_actions = len(diagnostic_data.get('recommended_actions', [])) > 0
        
        if audience == "support":
            if is_completed:
                opening = "Domain configuration verified. All records match requirements. What would you like to know?"
            elif has_conflicts:
                opening = "Diagnostic complete. Found conflicts requiring resolution. What specific issues can I clarify?"
            else:
                opening = f"Diagnostic complete for {diagnostic_data.get('domain')}. {len(diagnostic_data.get('recommended_actions', []))} action(s) required. What questions do you have?"
            
            suggested = [
                "What's the current nameserver configuration?",
                "Summarize the conflicts",
                "What actions are highest priority?",
                "Is this a subdomain or root domain setup?"
            ]
        else:  # customer
            if is_completed:
                opening = f"Great news! Your domain {diagnostic_data.get('domain')} is all set up correctly. Everything looks good! Do you have any questions?"
            elif has_conflicts:
                opening = f"I've finished checking {diagnostic_data.get('domain')}. I found a few things that need attention. What would you like to know?"
            elif has_actions:
                opening = f"I've analyzed {diagnostic_data.get('domain')} and have some recommendations for you. What questions can I answer?"
            else:
                opening = f"I've completed the diagnostic for {diagnostic_data.get('domain')}. How can I help you understand the results?"
            
            suggested = [
                "What do I need to do?",
                "Why isn't my domain working?",
                "Can you explain this in simple terms?",
                "Is this difficult to fix?"
            ]
        
        return {
            "opening_message": opening,
            "suggested_questions": suggested,
            "session_id": os.urandom(8).hex(),  # Generate session ID
            "grounded_in": diagnostic_data.get('domain'),
            "_metadata": {
                "audience": audience,
                "phase": 3
            }
        }
