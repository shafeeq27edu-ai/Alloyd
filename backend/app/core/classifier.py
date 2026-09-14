import re
from app.core.router import TaskCategory
from app.core.skills import SKILLS


class TaskClassifier:
    @classmethod
    def classify(cls, prompt: str) -> TaskCategory:
        for skill_name, skill in SKILLS.items():
            if f"@{skill_name}" in prompt:
                return TaskCategory(skill.category)

        writing_patterns = [r"write an essay", r"draft an email", r"write a blog", r"summarize"]
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in writing_patterns):
            return TaskCategory.WRITING

        image_patterns = [r"generate an image", r"draw a picture", r"create an image"]
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in image_patterns):
            return TaskCategory.IMAGE_GENERATION

        planning_patterns = [r"plan a", r"architecture", r"design a", r"how should I structure", r"strategy"]
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in planning_patterns):
            return TaskCategory.PLANNING_DECISION

        return TaskCategory.GENERAL
