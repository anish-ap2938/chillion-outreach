"""LLM client for Ollama and other open-source models"""
import httpx
from typing import Optional, List, Dict, Any
from app.config import settings
import json
import re


class LLMClient:
    """Client for calling Ollama or other LLM APIs"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model
        self.client = httpx.Client(timeout=120.0)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        """
        Call Ollama chat completion API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            json_mode: Whether to request JSON response
        
        Returns:
            Generated text response
        """
        # Format messages for Ollama
        formatted_messages = []
        
        if system_prompt:
            formatted_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        formatted_messages.extend(messages)
        
        # Build prompt for JSON mode if needed
        if json_mode:
            system_instruction = (
                "Respond with STRICT JSON only. No markdown, no code blocks, no explanations. "
                "Just the raw JSON object."
            )
            if system_prompt:
                system_prompt = f"{system_prompt}\n\n{system_instruction}"
            else:
                system_prompt = system_instruction
        
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except Exception as e:
            raise Exception(f"LLM API error: {str(e)}")
    
    def structured_completion(
        self,
        prompt: str,
        system_prompt: str,
        schema_description: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Get structured JSON response from LLM
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            schema_description: Optional description of expected JSON schema
            temperature: Lower temperature for more deterministic JSON
        
        Returns:
            Parsed JSON dict
        """
        full_system = system_prompt
        if schema_description:
            full_system += f"\n\nExpected JSON schema:\n{schema_description}"
        
        messages = [{"role": "user", "content": prompt}]
        
        raw_response = self.chat_completion(
            messages=messages,
            system_prompt=full_system,
            temperature=temperature,
            json_mode=True,
        )
        
        # Clean and parse JSON
        cleaned = raw_response.strip()
        
        # Remove markdown code fences if present
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from text by finding balanced braces
            start = cleaned.find("{")
            if start >= 0:
                # Find matching closing brace
                brace_count = 0
                end = start
                for i in range(start, len(cleaned)):
                    if cleaned[i] == "{":
                        brace_count += 1
                    elif cleaned[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                
                if end > start:
                    try:
                        candidate = cleaned[start:end]
                        # Try to fix common JSON issues
                        candidate = re.sub(r',\s*}', '}', candidate)  # Remove trailing commas
                        candidate = re.sub(r',\s*]', ']', candidate)
                        return json.loads(candidate)
                    except:
                        pass
            
            raise Exception(f"Failed to parse JSON from LLM response: {cleaned[:200]}")


# Global LLM client instance
llm_client = LLMClient(
    base_url=getattr(settings, "ollama_base_url", "http://localhost:11434"),
    model=getattr(settings, "ollama_model", "llama3"),
)

