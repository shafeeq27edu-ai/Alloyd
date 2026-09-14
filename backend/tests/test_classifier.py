import pytest
from app.core.classifier import TaskClassifier
from app.core.router import TaskCategory

def test_classify_explicit_skills():
    assert TaskClassifier.classify("@reviewer please look at this") == TaskCategory.CODING
    assert TaskClassifier.classify("@explainer how does this work?") == TaskCategory.CODING
    assert TaskClassifier.classify("@summarizer make this shorter") == TaskCategory.GENERAL
    assert TaskClassifier.classify("@writer draft an email") == TaskCategory.WRITING
    assert TaskClassifier.classify("@brainstormer let's think of ideas") == TaskCategory.PLANNING_DECISION
    assert TaskClassifier.classify("@researcher look into vector dbs") == TaskCategory.RESEARCH

def test_classify_coding_heuristics():
    assert TaskClassifier.classify("Fix this Python function.") == TaskCategory.CODING
    assert TaskClassifier.classify("Debug this FastAPI endpoint.") == TaskCategory.CODING
    assert TaskClassifier.classify("Why is my React component rendering twice?") == TaskCategory.CODING
    assert TaskClassifier.classify("Write a function that sorts this list.") == TaskCategory.CODING
    assert TaskClassifier.classify("Explain this SQL query.") == TaskCategory.CODING

def test_classify_research_heuristics():
    assert TaskClassifier.classify("Research vector databases for production use.") == TaskCategory.RESEARCH
    assert TaskClassifier.classify("Compare PostgreSQL and MongoDB.") == TaskCategory.RESEARCH
    assert TaskClassifier.classify("Analyze current approaches to RAG.") == TaskCategory.RESEARCH
    assert TaskClassifier.classify("Evaluate these three AI frameworks.") == TaskCategory.RESEARCH

def test_classify_writing_heuristics():
    assert TaskClassifier.classify("Write an essay on AI.") == TaskCategory.WRITING
    assert TaskClassifier.classify("Draft an email for my boss.") == TaskCategory.WRITING

def test_classify_general_fallback():
    # Ambiguous or generic terms should fall back to GENERAL
    assert TaskClassifier.classify("Tell me a joke.") == TaskCategory.GENERAL
    assert TaskClassifier.classify("Why is the ocean blue?") == TaskCategory.GENERAL
    assert TaskClassifier.classify("How are you?") == TaskCategory.GENERAL
    assert TaskClassifier.classify("What should I cook tonight?") == TaskCategory.GENERAL
    assert TaskClassifier.classify("Write a birthday message for my friend.") == TaskCategory.GENERAL
    assert TaskClassifier.classify("Explain how this works.") == TaskCategory.GENERAL
    assert TaskClassifier.classify("Analyze this text.") == TaskCategory.GENERAL
    assert TaskClassifier.classify("Build a small hut.") == TaskCategory.GENERAL
    assert TaskClassifier.classify("Code is running slow.") == TaskCategory.GENERAL
