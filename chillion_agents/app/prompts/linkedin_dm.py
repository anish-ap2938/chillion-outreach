"""LinkedIn DM prompt builder"""
from app.models.schemas import ProspectProfile, OfferContext


def build_linkedin_dm_prompt(
    prospect_profile: ProspectProfile,
    conversation_stage: str,  # Now accepts string
    offer_context: OfferContext,
    past_thread_summary: str = None,
    rag_context: str = "",
) -> str:
    """Build prompt for LinkedIn DM generation"""
    
    # Handle both string and enum
    stage_value = conversation_stage.value if hasattr(conversation_stage, 'value') else conversation_stage
    
    prompt = f"""You are a helpful finance automation advisor crafting a personalized LinkedIn message.

PROSPECT CONTEXT:
- Name: {prospect_profile.name}
- Title: {prospect_profile.title or "Not specified"}
- Company: {prospect_profile.company or "Not specified"}
- Industry: {prospect_profile.industry or "Not specified"}
- About: {prospect_profile.about_section or "Not available"}
- Recent Activity: {', '.join(prospect_profile.recent_posts or [])}

CONVERSATION STAGE: {stage_value}

CHILLION PRODUCT CONTEXT:
{rag_context}

PRODUCT OFFER:
- Product: {offer_context.product_name}
- Value Propositions:
{chr(10).join(f'  • {vp}' for vp in offer_context.value_propositions)}

"""
    
    if past_thread_summary:
        prompt += f"PREVIOUS CONVERSATION:\n{past_thread_summary}\n\n"
    
    prompt += """INSTRUCTIONS:
1. Write ONE short, personalized LinkedIn message (max 300 characters)
2. Reference something specific from their profile or recent activity (if available)
3. Anchor on their likely pain points (slow AR, high DSO, manual work)
4. Mention ONE key value proposition from Chillion
5. Use a friendly, professional, helpful tone - NOT salesy or spammy
6. End with a soft ask (e.g., "Would you be open to a quick conversation?")
7. Do NOT use hard selling language, exclamation marks, or pushy CTAs

Return ONLY the message text, nothing else."""
    
    return prompt

