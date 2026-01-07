"""LLM Prompt Management using HandyLLM format."""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class PromptManager:
    """Manages .hprompt template files and LLM interactions."""

    def __init__(self, prompts_dir: str = "app/core/prompts"):
        """Initialize prompt manager."""
        self.prompts_dir = Path(prompts_dir)
        self.prompts_cache: Dict[str, str] = {}
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load all .hprompt files into cache."""
        if not self.prompts_dir.exists():
            return

        for prompt_file in self.prompts_dir.glob("*.hprompt"):
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.prompts_cache[prompt_file.stem] = content

    def get_prompt(self, prompt_name: str) -> Optional[str]:
        """Get a prompt template by name."""
        if prompt_name not in self.prompts_cache:
            # Try to load if not cached
            prompt_path = self.prompts_dir / f"{prompt_name}.hprompt"
            if prompt_path.exists():
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.prompts_cache[prompt_name] = content
                    return content
            return None
        return self.prompts_cache[prompt_name]

    def render_prompt(
        self,
        prompt_name: str,
        variables: Dict[str, Any],
    ) -> Optional[str]:
        """Render a prompt with variables."""
        template = self.get_prompt(prompt_name)
        if not template:
            return None

        # Extract the human-friendly content (after ---)
        parts = template.split("---")
        if len(parts) >= 3:
            prompt_content = parts[2].strip()
        else:
            prompt_content = template

        # Simple template variable substitution
        # Convert variables to strings and handle missing values
        render_vars = {}
        for key, value in variables.items():
            if isinstance(value, (dict, list)):
                render_vars[key] = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                render_vars[key] = str(value) if value is not None else ""

        # Replace {{variable}} with values
        result = prompt_content
        for key, value in render_vars.items():
            result = result.replace(f"{{{{{key}}}}}", value)

        return result

    def list_prompts(self) -> list:
        """List all available prompts."""
        return list(self.prompts_cache.keys())


# Global prompt manager instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get or create the global prompt manager."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
