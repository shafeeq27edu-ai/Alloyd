from enum import Enum
import re
from typing import Tuple

class TaskCategory(Enum):
    CODE = "CODE"
    LONG_CONTEXT = "LONG_CONTEXT"
    WRITING = "WRITING"
    FAST_GENERAL = "FAST_GENERAL"
    MULTIMODAL = "MULTIMODAL"

class RuleRouter:
    # provider_name, model_name
    ROUTES = {
        TaskCategory.CODE: ("openai", "gpt-4o"),
        TaskCategory.LONG_CONTEXT: ("gemini", "gemini-1.5-pro"),
        TaskCategory.WRITING: ("openai", "gpt-4o"),
        TaskCategory.MULTIMODAL: ("gemini", "gemini-1.5-pro"),
        TaskCategory.FAST_GENERAL: ("groq", "llama3-8b-8192")
    }

    @classmethod
    def classify_task(cls, prompt: str) -> TaskCategory:
        # Long context check
        if len(prompt) > 8000:
            return TaskCategory.LONG_CONTEXT
            
        # Code check
        code_patterns = [
            r"def\s+", r"class\s+", r"import\s+", r"function\(", 
            r"```python", r"```javascript", r"```ts", r"```go"
        ]
        if any(re.search(pattern, prompt) for pattern in code_patterns):
            return TaskCategory.CODE
            
        # Writing check
        writing_patterns = [
            r"write an essay", r"draft an email", r"write a blog", r"summarize"
        ]
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in writing_patterns):
            return TaskCategory.WRITING
            
        # Fallback
        return TaskCategory.FAST_GENERAL

    @classmethod
    def route(cls, prompt: str) -> Tuple[str, str]:
        """Returns (provider_name, model_name)"""
        category = cls.classify_task(prompt)
        return cls.ROUTES[category]
