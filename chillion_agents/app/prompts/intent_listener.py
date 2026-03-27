"""Intent listener prompt builder"""


def build_intent_classification_prompt(item_text: str, keywords: list) -> str:
    """Build prompt for intent classification"""

    prompt = f"""You are an intent classification system for Chillion IT & Consultancy Pvt. Ltd.

CHILLION SOLUTION AREAS:
- IT Infrastructure & Enterprise Solutions
- Cyber Security & Managed Services
- Cloud, Data Center, SaaS & PaaS
- Software Licensing & Digital Solutions
- Defense Technologies & Specialized Engineering
- Precision Engineering, Optics & Photonics
- RF, Microwave & Antenna Solutions

KEYWORDS TO MATCH: {', '.join(keywords)}

CONTENT TO ANALYZE:
{item_text}

INSTRUCTIONS:
1. Determine if this content shows INTENT (someone discussing problems Chillion solves)
2. Score intent from 1-5 (1=no intent, 5=strong intent)
3. Map to problem category (e.g., "IT Infrastructure", "Cyber Security", "Defense Engineering")
4. Map to related Chillion solution area
5. Assess urgency (high/medium/low)

Return JSON:
{{
  "is_relevant": true/false,
  "intent_score": 1-5,
  "problem_category": "category name",
  "related_product": "solution area name",
  "urgency": "high/medium/low",
  "reasoning": "brief explanation"
}}"""

    return prompt
