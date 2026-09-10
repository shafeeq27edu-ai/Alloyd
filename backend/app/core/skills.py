class Skill:
    def __init__(self, name: str, category: str, system_prompt: str):
        self.name = name
        self.category = category
        self.system_prompt = system_prompt

SKILLS = {
    "architect": Skill(
        name="architect",
        category="PLANNING_DECISION",
        system_prompt="You are an expert system architect. Make technical decisions."
    ),
    "copywriter": Skill(
        name="copywriter",
        category="WRITING",
        system_prompt="You are an expert copywriter. Write engaging content."
    ),
    "artist": Skill(
        name="artist",
        category="IMAGE_GENERATION",
        system_prompt="You are an AI artist. Generate detailed image prompts."
    )
}
