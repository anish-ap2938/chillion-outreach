"""Intent Listener Agent - finds and scores intent signals"""
from app.agents.base import BaseAgent
from app.models.schemas import IntentListenerInput, IntentListenerOutput, IntentRecord
from app.prompts.intent_listener import build_intent_classification_prompt
from app.config import settings


class IntentListenerAgent(BaseAgent[IntentListenerInput, IntentListenerOutput]):
    """Agent that finds and scores intent signals from web feeds"""
    
    def process(self, input_data: IntentListenerInput) -> IntentListenerOutput:
        """Process feed items and generate intent records"""
        try:
            intent_records = []
            relevant_count = 0
            
            for item in input_data.feed_items:
                # Classify intent for each item
                is_relevant, score, category, product = self._classify_intent(
                    item, input_data.keywords
                )
                
                if is_relevant and score >= 3:  # Only include medium-high intent
                    record = IntentRecord(
                        source_platform=item.platform,
                        url=item.url,
                        author_name=item.author,
                        author_handle=item.author_handle,
                        company_if_detectable=self._extract_company(item),
                        raw_text=item.text_snippet,
                        intent_score_one_to_five=score,
                        problem_category=category,
                        related_product=product,
                        urgency_tag=self._determine_urgency(score, item),
                        notes_for_sales=self._generate_sales_notes(item, category),
                    )
                    intent_records.append(record)
                    relevant_count += 1
            
            output = IntentListenerOutput(
                intent_records=intent_records,
                total_processed=len(input_data.feed_items),
                relevant_count=relevant_count,
            )
            
            self.log_event("intent_processed", {
                "total": len(input_data.feed_items),
                "relevant": relevant_count,
            })
            
            return output
            
        except Exception as e:
            self.log_event("error", {"error": str(e)})
            raise
    
    def _classify_intent(self, item, keywords: list) -> tuple[bool, int, str, str]:
        """Classify if item shows intent and map to Chillion product using LLM"""
        from app.prompts.intent_listener import build_intent_classification_prompt
        from app.llm.client import llm_client
        
        try:
            # Build classification prompt
            user_prompt = build_intent_classification_prompt(item.text_snippet, keywords)
            
            system_prompt = (
                "You are an intent classification system for Chillion. "
                "Analyze content and determine if it shows buying intent for finance automation solutions. "
                "Return valid JSON only."
            )
            
            schema_description = """{
  "is_relevant": true/false,
  "intent_score": 1-5,
  "problem_category": "category name",
  "related_product": "product name",
  "urgency": "high/medium/low"
}"""
            
            # Call LLM for classification
            result = llm_client.structured_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema_description=schema_description,
                temperature=0.3,  # Lower temperature for more consistent classification
            )
            
            is_relevant = result.get("is_relevant", False)
            if not is_relevant:
                return False, 1, "", ""
            
            score = result.get("intent_score", 1)
            category = result.get("problem_category", "General Finance Automation")
            product = result.get("related_product", "Order to Cash Automation")
            
            return True, score, category, product
            
        except Exception as e:
            # Fallback to simple keyword matching if LLM fails
            self.log_event("intent_classification_fallback", {"error": str(e)})
            return self._classify_intent_keyword_fallback(item, keywords)
    
    def _classify_intent_keyword_fallback(self, item, keywords: list) -> tuple[bool, int, str, str]:
        """Fallback keyword-based classification"""
        text_lower = item.text_snippet.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        
        if matches == 0:
            return False, 1, "", ""
        
        if any(kw in text_lower for kw in ["deduction", "chargeback"]):
            category = "Deductions Management"
            product = "Deductions Management"
        elif any(kw in text_lower for kw in ["invoice", "document", "processing"]):
            category = "Document Processing"
            product = "Gia Docs"
        elif any(kw in text_lower for kw in ["ar", "accounts receivable", "collections"]):
            category = "AR Automation"
            product = "Order to Cash Automation"
        elif any(kw in text_lower for kw in ["dso", "cash flow", "payment"]):
            category = "Cash Flow Optimization"
            product = "Order to Cash Analytics"
        else:
            category = "General Finance Automation"
            product = "Order to Cash Automation"
        
        score = min(5, 2 + matches)
        if any(word in text_lower for word in ["urgent", "need", "problem", "issue"]):
            score = min(5, score + 1)
        
        return True, score, category, product
    
    def _extract_company(self, item) -> str:
        """Extract company name from item (placeholder)"""
        # TODO: Use NER or LLM to extract company
        return None
    
    def _determine_urgency(self, score: int, item) -> str:
        """Determine urgency tag"""
        if score >= 4:
            return "high"
        elif score >= 3:
            return "medium"
        return "low"
    
    def _generate_sales_notes(self, item, category: str) -> str:
        """Generate notes for sales team"""
        return f"Found discussing {category}. Original context: {item.text_snippet[:200]}"

