import re
from app.core.router import TaskCategory
from app.core.skills import SKILLS


class TaskClassifier:
    @classmethod
    def classify(cls, prompt: str) -> TaskCategory:
        for skill_name, skill in SKILLS.items():
            if f"@{skill_name}" in prompt:
                return TaskCategory(skill.category)

        # Avoid single-word matches for verbs like 'explain', 'code', 'research'
        coding_patterns = [
            r"fix this \w+", r"debug this", r"component rendering",
            r"write a function", r"explain this (sql|query|code|function|script)",
            r"how do i (implement|code) a", r"error in my code",
            r"traceback", r"refactor this"
        ]
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in coding_patterns):
            return TaskCategory.CODING

        research_patterns = [
            r"research .* for production", r"compare .* and .*",
            r"analyze .* approaches to", r"evaluate these",
            r"pros and cons of", r"what are the differences between"
        ]
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in research_patterns):
            return TaskCategory.RESEARCH

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
