from aether_sidecar.safety import evaluate_message


def test_safety_blocklist_match():
    result = evaluate_message("you should kill yourself")
    assert result.blocked is True
    assert "kill yourself" in result.flags


def test_safety_clean_message():
    result = evaluate_message("how do i survive first night?")
    assert result.blocked is False
