from app.core.history import trim_history


def test_history_under_budget_is_unchanged():
    messages = [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    trimmed, dropped = trim_history(messages, 1000)
    assert trimmed == messages
    assert dropped == 0


def test_history_over_budget_drops_oldest_messages():
    messages = [
        {"role": "user", "content": "a" * 40},
        {"role": "assistant", "content": "b" * 40},
        {"role": "user", "content": "c" * 40},
        {"role": "assistant", "content": "d" * 40},
        {"role": "user", "content": "latest"},
    ]
    trimmed, dropped = trim_history(messages, 100)

    assert dropped == 2
    assert trimmed == [
        {"role": "user", "content": "c" * 40},
        {"role": "assistant", "content": "d" * 40},
        {"role": "user", "content": "latest"},
    ]


def test_history_keeps_system_prompt_outside_the_budget():
    messages = [
        {"role": "system", "content": "s" * 50},
        {"role": "user", "content": "u" * 50},
        {"role": "assistant", "content": "a" * 50},
        {"role": "user", "content": "latest"},
    ]
    trimmed, dropped = trim_history(messages, 60)

    assert trimmed[0] == {"role": "system", "content": "s" * 50}
    assert trimmed[-1] == {"role": "user", "content": "latest"}
    assert dropped == 2


def test_history_always_keeps_the_latest_message():
    messages = [
        {"role": "user", "content": "x" * 500},
        {"role": "user", "content": "y" * 500},
    ]
    trimmed, dropped = trim_history(messages, 10)

    assert trimmed == [{"role": "user", "content": "y" * 500}]
    assert dropped == 1


def test_history_with_only_system_messages():
    messages = [{"role": "system", "content": "rules"}]
    trimmed, dropped = trim_history(messages, 1)
    assert trimmed == messages
    assert dropped == 0


def test_history_budget_disabled_keeps_everything():
    messages = [
        {"role": "user", "content": "a" * 100},
        {"role": "user", "content": "b" * 100},
    ]
    trimmed, dropped = trim_history(messages, 0)
    assert trimmed == messages
    assert dropped == 0
