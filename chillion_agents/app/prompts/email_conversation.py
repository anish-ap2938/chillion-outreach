"""Email conversation prompt builder"""
from app.models.schemas import CompanyContext


def build_email_prompt(
    prospect,  # Accept any prospect-like object
    company_context: CompanyContext,
    conversation_stage: str,  # Now accepts string
    thread_summary: str = None,
    rag_context: str = "",
) -> str:
    """Build prompt for email generation"""
    
    # Handle both string and enum
    stage_value = conversation_stage.value if hasattr(conversation_stage, 'value') else conversation_stage
    
    # Handle prospect fields safely
    prospect_name = getattr(prospect, 'name', 'Unknown')
    prospect_title = getattr(prospect, 'title', None) or "Not specified"
    prospect_problem = getattr(prospect, 'problem_category', None) or "General finance automation"
    
    prompt = f"""You are a B2B sales professional writing a professional email for Chillion.

PROSPECT:
- Name: {prospect_name}
- Title: {prospect_title}
- Company: {company_context.name}
- Industry: {company_context.industry or "Not specified"}
- Problem Category: {prospect_problem}

CONVERSATION STAGE: {stage_value}

CHILLION PRODUCT CONTEXT:
{rag_context}

"""
    
    if thread_summary:
        prompt += f"PREVIOUS EMAIL THREAD:\n{thread_summary}\n\n"
    
    stage_guidance = {
        "not_contacted": "Focus on problem awareness and insight. Introduce Chillion briefly.",
        "first_touch_sent": "Follow up gently. Provide value (insight, case study, resource).",
        "replied": "Respond to their specific question or concern. Move toward next step.",
        "meeting_booked": "Confirm meeting details and prepare them for the conversation.",
    }
    
    prompt += f"""INSTRUCTIONS:
1. Write a SHORT, CLEAR B2B email (3-4 paragraphs max)
2. Stage guidance: {stage_guidance.get(stage_value, "Professional follow-up")}
3. Focus on ONE main idea per email
4. For early stage: Focus on problem and insight
5. For later stage: Focus on demo, case study, or next step
6. Always include an easy way to say "no" or "not now" (e.g., "If this isn't the right time, no worries!")
7. Use professional but conversational tone
8. Include a clear, soft call-to-action

Return the email in this JSON format:
{{
  "subject": "Subject line (max 60 chars)",
  "body_text": "Plain text version",
  "body_html": "HTML version (simple, clean)",
  "call_to_action": "CTA text"
}}"""
    
    return prompt

