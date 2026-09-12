import re
from app.core.router import TaskCategory
from app.core.skills import SKILLS
from app.providers.groq_adapter import GroqAdapter

class TaskClassifier:
    @classmethod
    async def classify(cls, prompt: str, groq_api_key: str | None = None) -> TaskCategory:
        for skill_name, skill in SKILLS.items():
            if f"@{skill_name}" in prompt:
                return TaskCategory(skill.category)

        writing_patterns = [r"write an essay", r"draft an email", r"write a blog", r"summarize"]
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in writing_patterns):
            return TaskCategory.WRITING

        image_patterns = [r"generate an image", r"draw a picture"]
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in image_patterns):
            return TaskCategory.IMAGE_GENERATION

        if groq_api_key:
            try:
                adapter = GroqAdapter()
                messages = [
                    {"role": "system", "content": "You are a classifier. Reply with exactly one word: PLANNING_DECISION or GENERAL."},
                    {"role": "user", "content": prompt}
                ]
                response = await adapter.send_message(groq_api_key, "llama3-8b-8192", messages)
                if "PLANNING_DECISION" in response.upper():
                    return TaskCategory.PLANNING_DECISION
            except Exception:
                pass

        return TaskCategory.GENERAL
