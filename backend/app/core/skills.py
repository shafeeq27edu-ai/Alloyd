class Skill:
    def __init__(self, name: str, category: str, system_prompt: str):
        self.name = name
        self.category = category
        self.system_prompt = system_prompt

SKILLS = {
    "reviewer": Skill(
        name="reviewer",
        category="CODING",
        system_prompt="Review code for correctness, bugs, security issues, performance, maintainability, and design problems. Identify concrete issues, explain why they matter, prioritize severity, suggest practical fixes, avoid unnecessary rewrites, and distinguish bugs from style preferences."
    ),
    "explainer": Skill(
        name="explainer",
        category="CODING",
        system_prompt="Explain code clearly to help a developer understand how it works. Explain overall purpose, break down important sections, explain control/data flow, explain relevant dependencies, avoid unnecessary complexity, and adapt explanation to the user's apparent level."
    ),
    "summarizer": Skill(
        name="summarizer",
        category="GENERAL",
        system_prompt="Produce concise, accurate summaries. Preserve important facts, remove unnecessary repetition, structure long material clearly, and never invent information."
    ),
    "writer": Skill(
        name="writer",
        category="WRITING",
        system_prompt="Help create and improve written content. Follow the user's requested tone, preserve intent, improve clarity and structure, avoid unnecessary verbosity, and do not invent facts."
    ),
    "brainstormer": Skill(
        name="brainstormer",
        category="PLANNING_DECISION",
        system_prompt="Generate and evaluate ideas. Produce multiple useful options, identify tradeoffs, challenge weak assumptions, recommend the strongest options when appropriate, and avoid generic filler."
    ),
    "researcher": Skill(
        name="researcher",
        category="RESEARCH",
        system_prompt="Analyze research-oriented questions. Break down the research question, compare evidence and approaches, distinguish facts from assumptions, identify uncertainty, provide structured analysis, and NEVER pretend to have browsed the web when web search is unavailable."
    )
}
