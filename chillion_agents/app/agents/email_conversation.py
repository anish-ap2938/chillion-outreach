"""Email Conversation Agent - generates B2B email messages"""
from app.agents.base import BaseAgent
from app.models.schemas import EmailConversationInput, EmailConversationOutput
from app.prompts.templates import (
    CHILLION_PRODUCTS,
    EMAIL_TEMPLATES,
    get_product_info,
    get_email_template,
    format_template
)
from app.llm.client import llm_client


class EmailConversationAgent(BaseAgent[EmailConversationInput, EmailConversationOutput]):
    """Agent that generates professional B2B emails"""
    
    def process(self, input_data: EmailConversationInput) -> EmailConversationOutput:
        """Generate a professional email"""
        try:
            # Get product info
            product_key = input_data.product_key or "it_infrastructure"
            product = get_product_info(product_key)
            
            # Get template if specified
            template_key = input_data.template_key or "custom"
            template = get_email_template(template_key)
            
            # Extract prospect info
            prospect = input_data.prospect_record
            company = input_data.company_context
            
            # Handle conversation_stage as string
            stage = input_data.conversation_stage
            if hasattr(stage, 'value'):
                stage = stage.value
            
            # Prepare template variables
            template_vars = {
                "first_name": prospect.name.split()[0] if prospect.name else "there",
                "full_name": prospect.name or "",
                "company_name": company.name or "",
                "industry": company.industry or "your industry",
                "job_title": prospect.title or "",
                "sender_name": "[Your Name]",
                "sender_title": "[Your Title]",
            }
            
            # If using a predefined template, format it
            if template_key != "custom" and template.get("body"):
                subject = format_template(template["subject"], **template_vars)
                body_text = format_template(template["body"], **template_vars)
                body_text = self._append_opt_out(body_text, input_data.opt_out_note)
                body_html = body_text.replace("\n", "<br>").replace("•", "&#8226;")
                cta = "Schedule a brief demo"
                
                output = EmailConversationOutput(
                    subject_line=subject,
                    body_html=body_html,
                    body_text=body_text,
                    call_to_action=cta,
                    follow_up_suggestion_days=5,
                )
                
                self._audit_generated_message(subject, body_text, channel="email")
                self._maybe_validate_deliverability(output, input_data)
                return output
            
            # Otherwise, generate with LLM
            rag_context = self.retrieve_rag_context(product["name"])
            
            # Build prompt with product info and templates as examples
            user_prompt = self._build_prompt(
                prospect=prospect,
                company=company,
                stage=stage,
                product=product,
                template_vars=template_vars,
                rag_context=rag_context,
                custom_message=input_data.custom_message,
            )
            
            system_prompt = """You are a professional B2B sales email writer for Chillion.
Write clear, concise, professional emails. Focus on value, not features.
Always return valid JSON with: subject, body_text, body_html, call_to_action"""
            
            schema_description = """{
  "subject": "Email subject line (max 60 characters)",
  "body_text": "Plain text email body",
  "body_html": "HTML version (use <br> for newlines, <b> for bold)",
  "call_to_action": "CTA text"
}"""
            
            email_data = llm_client.structured_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema_description=schema_description,
                temperature=0.7,
            )
            
            subject = email_data.get("subject", f"Improving {company.name}'s receivables process")
            body_text = email_data.get("body_text", "")
            body_text = self._append_opt_out(body_text, input_data.opt_out_note)
            body_html = email_data.get("body_html", body_text.replace("\n", "<br>"))
            cta = email_data.get("call_to_action", "Schedule a brief conversation")
            
            output = EmailConversationOutput(
                subject_line=subject,
                body_html=body_html,
                body_text=body_text,
                call_to_action=cta,
                follow_up_suggestion_days=3 if stage == "not_contacted" else 5,
            )
            
            self._audit_generated_message(subject, body_text, channel="email")
            self._maybe_validate_deliverability(output, input_data)
            self.log_event("draft_created", {"prospect_id": prospect.id if prospect.id else "new"})
            return output
            
        except Exception as e:
            self.log_event("error", {"error": str(e)})
            # Return a fallback response instead of raising
            return self._fallback_response(input_data)
    
    def _build_prompt(self, prospect, company, stage, product, template_vars, rag_context, custom_message=None):
        """Build the LLM prompt"""
        
        example_template = EMAIL_TEMPLATES.get("ar_visibility", {})
        
        prompt = f"""Generate a professional B2B sales email for Chillion.

RECIPIENT:
- Name: {prospect.name or "Unknown"}
- Title: {prospect.title or "Finance Executive"}
- Company: {company.name or "Unknown Company"}
- Industry: {company.industry or "Enterprise"}

PRODUCT TO PITCH:
- Product: {product["name"]}
- Description: {product["description"]}
- Key Features:
{chr(10).join(f"  • {f}" for f in product["key_features"])}
- Pain Points We Solve:
{chr(10).join(f"  • {p}" for p in product["pain_points"])}

STAGE: {stage}

"""
        if custom_message:
            prompt += f"""
USER'S MESSAGE/CONTEXT:
{custom_message}

"""

        if rag_context:
            prompt += f"""
CHILLION PRODUCT KNOWLEDGE:
{rag_context[:1500]}

"""
        
        prompt += f"""
EXAMPLE EMAIL (use as reference for tone and structure):
Subject: {example_template.get("subject", "Enterprise AR visibility")}
{example_template.get("body", "")[:500]}...

INSTRUCTIONS:
1. Write a SHORT, professional B2B email (3-4 paragraphs max)
2. Open by acknowledging a common pain point in their industry
3. Briefly mention how Chillion solves it (2-3 bullet points max)
4. Include a soft CTA (offer a demo or quick call)
5. Be conversational but professional - NOT salesy or pushy
6. Use the recipient's first name: {template_vars["first_name"]}

Return JSON with: subject, body_text, body_html, call_to_action"""
        
        return prompt
    
    def _fallback_response(self, input_data) -> EmailConversationOutput:
        """Generate a fallback response if LLM fails"""
        prospect = input_data.prospect_record
        company = input_data.company_context
        first_name = prospect.name.split()[0] if prospect.name else "there"
        
        subject = f"Infrastructure and engineering support for {company.name or 'your team'}"
        body_text = f"""Hi {first_name},

Many enterprise and government teams we work with are consolidating IT infrastructure, security, and engineering delivery under one accountable partner instead of juggling multiple vendors.

Chillion supports programs across IT infrastructure, cyber security, cloud, software licensing, and advanced engineering — with pan-India delivery from Hyderabad.

If you are scoping vendors for an upcoming program, I would welcome a brief conversation.

Thanks,
[Your Name]
Chillion IT & Consultancy Pvt. Ltd.
https://www.chillion.in"""
        
        return EmailConversationOutput(
            subject_line=subject,
            body_html=body_text.replace("\n", "<br>"),
            body_text=body_text,
            call_to_action="Schedule a brief demo",
            follow_up_suggestion_days=5,
        )

    # =============== Helpers ===============
    def _append_opt_out(self, body_text: str, opt_out_note: str | None) -> str:
        """Append opt-out note if provided."""
        if opt_out_note:
            return f"{body_text}\n\n{opt_out_note}"
        return body_text

    def _mask_pii(self, text: str) -> str:
        """Basic PII masking for audit logs (emails + long digit sequences)."""
        import re

        text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[masked_email]", text)
        text = re.sub(r"\b\d{6,}\b", "[masked_number]", text)
        return text

    def _audit_generated_message(self, subject: str, body_text: str, channel: str):
        """Audit log with masked content."""
        masked_subject = self._mask_pii(subject or "")
        masked_body = self._mask_pii(body_text or "")
        self.log_event(
            "draft_audit",
            {"channel": channel, "subject": masked_subject, "body_preview": masked_body[:500]},
        )

    def _maybe_validate_deliverability(self, output: EmailConversationOutput, input_data: EmailConversationInput):
        """Run a stubbed deliverability check when requested."""
        if not input_data.validate_before_send:
            return

        is_deliverable = self._stub_deliverability_check(output.body_text)
        self.log_event(
            "deliverability_check",
            {"prospect": input_data.prospect_record.name, "result": "pass" if is_deliverable else "warn"},
        )

    def _stub_deliverability_check(self, body_text: str) -> bool:
        """
        Local-only deliverability stub.
        Returns True but could be extended to run basic linting (e.g., link count, spam words).
        """
        _ = body_text  # placeholder for future heuristics
        return True
