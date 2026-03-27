"""LinkedIn DM Agent - generates personalized LinkedIn messages"""
from app.agents.base import BaseAgent
from app.models.schemas import LinkedInDMInput, LinkedInDMOutput
from app.prompts.templates import (
    CHILLION_PRODUCTS,
    LINKEDIN_TEMPLATES,
    get_product_info,
    get_linkedin_template,
    format_template
)
from app.llm.client import llm_client
import re


class LinkedInDMAgent(BaseAgent[LinkedInDMInput, LinkedInDMOutput]):
    """Agent that generates personalized LinkedIn DMs"""
    
    def process(self, input_data: LinkedInDMInput) -> LinkedInDMOutput:
        """Generate a personalized LinkedIn DM"""
        try:
            # Get product info
            product_key = input_data.product_key or "it_infrastructure"
            product = get_product_info(product_key)
            
            # Get template if specified
            template_key = input_data.template_key or "custom"
            template = get_linkedin_template(template_key)
            
            # Handle conversation_stage as string
            stage = input_data.conversation_stage
            if hasattr(stage, 'value'):
                stage = stage.value
            
            # Prepare template variables
            profile = input_data.prospect_profile
            template_vars = {
                "first_name": profile.name.split()[0] if profile.name else "there",
                "full_name": profile.name or "",
                "company_name": profile.company or "",
                "industry": profile.industry or "your industry",
                "job_title": profile.title or "",
                "sender_name": "[Your Name]",
            }
            
            # If using a predefined template, format it
            if template_key != "custom" and template.get("message"):
                message_text = format_template(template["message"], **template_vars)
                
                output = LinkedInDMOutput(
                    stage=stage,
                    message_type="new_outreach" if stage == "not_contacted" else "follow_up",
                    message_text=message_text,
                    personalization_notes=f"Used template: {template['name']}",
                    suggested_follow_up_window_days=3,
                )
                self._audit_generated_message(output)
                return output
            
            # Otherwise, generate with LLM
            rag_context = self.retrieve_rag_context(product["name"])
            
            user_prompt = self._build_prompt(
                profile=profile,
                stage=stage,
                product=product,
                template_vars=template_vars,
                rag_context=rag_context,
                custom_message=input_data.custom_message,
            )
            
            system_prompt = """You are a B2B technology advisor at Chillion crafting personalized LinkedIn messages.
Write in a friendly, professional, human tone. Be concise - max 300 characters.
Return ONLY the message text, nothing else."""
            
            message_text = llm_client.chat_completion(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                temperature=0.7,
            )
            
            # Clean up the response
            message_text = message_text.strip()
            if message_text.startswith('"') and message_text.endswith('"'):
                message_text = message_text[1:-1]
            if message_text.startswith("```"):
                message_text = message_text.split("```")[1] if "```" in message_text[3:] else message_text[3:]
            
            output = LinkedInDMOutput(
                stage=stage,
                message_type="new_outreach" if stage == "not_contacted" else "reply",
                message_text=message_text,
                personalization_notes=self._extract_personalization_notes(input_data, product),
                suggested_follow_up_window_days=3,
            )
            
            self.log_event("draft_created", {"prospect": profile.name})
            self._audit_generated_message(output)
            return output
            
        except Exception as e:
            self.log_event("error", {"error": str(e)})
            # Return fallback instead of raising
            return self._fallback_response(input_data)
    
    def _build_prompt(self, profile, stage, product, template_vars, rag_context, custom_message=None):
        """Build the LLM prompt"""
        
        # Get example templates for reference
        examples = "\n".join([
            f"Example ({name}): {t['message'][:150]}..."
            for name, t in list(LINKEDIN_TEMPLATES.items())[:2]
            if t.get("message")
        ])
        
        prompt = f"""Generate a personalized LinkedIn message for Chillion sales outreach.

RECIPIENT:
- Name: {profile.name or "Unknown"}
- Title: {profile.title or "Not specified"}
- Company: {profile.company or "Not specified"}
- Industry: {profile.industry or "Not specified"}
- About: {profile.about_section or "Not available"}
- Recent Posts/Activity: {', '.join(profile.recent_posts or []) or "None available"}

PRODUCT TO PITCH:
- Product: {product["name"]}
- Key Value Props: {', '.join(product["key_features"][:2])}
- Pain Points: {', '.join(product["pain_points"][:2])}

STAGE: {stage}

"""
        if custom_message:
            prompt += f"""
USER'S MESSAGE/CONTEXT:
{custom_message}

"""
        
        if rag_context:
            prompt += f"""
PRODUCT KNOWLEDGE:
{rag_context[:800]}

"""
        
        prompt += f"""
EXAMPLE MESSAGES (for tone reference):
{examples}

INSTRUCTIONS:
1. Write ONE short LinkedIn message (max 300 characters)
2. Reference something specific about them if available
3. Focus on their likely pain points and how Chillion helps
4. Use a friendly, professional tone - NOT salesy
5. End with a soft ask or question
6. Use their first name: {template_vars["first_name"]}

Return ONLY the message text, nothing else."""
        
        return prompt
    
    def _extract_personalization_notes(self, input_data: LinkedInDMInput, product: dict) -> str:
        """Extract notes explaining personalization choices"""
        notes = []
        if input_data.prospect_profile.title:
            notes.append(f"Referenced role: {input_data.prospect_profile.title}")
        if input_data.prospect_profile.recent_posts:
            notes.append("Referenced recent activity")
        notes.append(f"Product focus: {product['short_name']}")
        return "; ".join(notes) if notes else "Standard outreach"
    
    def _fallback_response(self, input_data) -> LinkedInDMOutput:
        """Generate a fallback response if LLM fails"""
        profile = input_data.prospect_profile
        first_name = profile.name.split()[0] if profile.name else "there"
        company = profile.company or "your company"
        
        stage = input_data.conversation_stage
        if hasattr(stage, 'value'):
            stage = stage.value
        
        message = f"""Hi {first_name},

I noticed your work at {company} in technology and engineering programs. Chillion helps teams with IT infrastructure, cyber security, cloud, and specialized engineering delivery across India.

Open to a quick chat?"""
        
        return LinkedInDMOutput(
            stage=stage,
            message_type="new_outreach",
            message_text=message,
            personalization_notes="Fallback template used",
            suggested_follow_up_window_days=3,
        )

    # =============== Helpers ===============
    def _mask_pii(self, text: str) -> str:
        """Basic PII masking for audit logs (emails + long digit sequences)."""
        text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[masked_email]", text)
        text = re.sub(r"\b\d{6,}\b", "[masked_number]", text)
        return text

    def _audit_generated_message(self, output: LinkedInDMOutput):
        """Audit log with masked content."""
        masked_body = self._mask_pii(output.message_text or "")
        self.log_event(
            "draft_audit",
            {
                "channel": "linkedin",
                "stage": output.stage,
                "body_preview": masked_body[:500],
            },
        )
