from typing import Dict, List, Tuple


def trim_history(
    messages: List[Dict[str, str]], max_chars: int
) -> Tuple[List[Dict[str, str]], int]:
    """Keep system prompts and the newest turns within an approximate character budget.

    Returns the trimmed list and how many non-system messages were dropped.
    The latest message is always kept so the current turn is never discarded.
    """
    if max_chars <= 0:
        return list(messages), 0

    system = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    if not rest:
        return list(messages), 0

    budget = max(max_chars - sum(len(m.get("content") or "") for m in system), 0)
    kept_reversed: List[Dict[str, str]] = []
    used = 0
    for message in reversed(rest):
        cost = len(message.get("content") or "")
        if kept_reversed and used + cost > budget:
            break
        kept_reversed.append(message)
        used += cost

    kept = list(reversed(kept_reversed))
    return system + kept, len(rest) - len(kept)
