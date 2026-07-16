import os
import jinja2
from typing import Dict, Any

class PromptManager:
    """Manages prompt template loading, validation, rendering and caching."""
    
    def __init__(self):
        # Setup Jinja file template loader
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.template_dir = os.path.join(current_dir, "prompts")
        self.jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.template_dir))
        self.cache: Dict[str, Any] = {}

    def get_template(self, template_name: str):
        """Fetches and caches templates to prevent redundant IO."""
        if template_name in self.cache:
            return self.cache[template_name]
        
        try:
            template = self.jinja_env.get_template(template_name)
            self.cache[template_name] = template
            return template
        except Exception as e:
            print(f"Jinja template {template_name} failed to load from file: {e}")
            raise e

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Renders the template with the provided context dictionary."""
        try:
            template = self.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            print(f"Failed to render {template_name}: {e}. Running fallback.")
            # Fallback patterns to prevent runtime crashes
            if "chat" in template_name:
                return f"History:\n{context.get('history')}\n\nContext:\n{context.get('retrieved_context')}\n\nQuery:\n{context.get('query')}"
            elif "summary" in template_name:
                return f"Summarize conversation:\n{context.get('history')}"
            elif "clause" in template_name:
                return f"Explain clause:\n{context.get('clause')}\nContext:\n{context.get('context')}"
            elif "followup" in template_name:
                return f"Generate followups for:\n{context.get('history')}"
            return str(context)

    def scan_for_prompt_injection(self, text: str) -> bool:
        """Validates input text against known prompt injection and jailbreak signatures."""
        if not text:
            return False
            
        text_lower = text.lower()
        injection_keywords = [
            "ignore previous instructions",
            "ignore all instructions",
            "forget previous",
            "forget what you were",
            "you are now a",
            "you are now an",
            "jailbreak",
            "override instructions",
            "system prompt bypass",
            "ignore the rules"
        ]
        
        for keyword in injection_keywords:
            if keyword in text_lower:
                return True
        return False
