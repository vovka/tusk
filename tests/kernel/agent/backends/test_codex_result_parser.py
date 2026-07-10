from tusk.kernel.agent.backends.codex_result_parser import CodexResultParser

SUCCESS_STREAM = "\n".join([
    '{"type":"thread.started","thread_id":"t"}',
    '{"type":"turn.started"}',
    '{"type":"item.completed","item":{"id":"item_0","type":"agent_message",'
    '"text":"{\\"status\\":\\"success\\",\\"reply\\":\\"Hi\\",\\"final_text\\":\\"Hi\\"}"}}',
    '{"type":"turn.completed","usage":{}}',
])


def test_parser_extracts_final_agent_message_payload() -> None:
    result = CodexResultParser().parse(SUCCESS_STREAM)
    assert result == {"status": "success", "reply": "Hi", "final_text": "Hi"}


def test_parser_returns_last_agent_message_when_multiple() -> None:
    stream = "\n".join([
        '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"reply\\":\\"first\\"}"}}',
        '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"reply\\":\\"second\\"}"}}',
    ])
    assert CodexResultParser().parse(stream) == {"reply": "second"}


def test_parser_ignores_non_agent_message_items() -> None:
    stream = '{"type":"item.completed","item":{"type":"command_execution","command":"ls"}}'
    assert CodexResultParser().parse(stream) is None


def test_parser_returns_none_when_no_agent_message() -> None:
    stream = '{"type":"turn.failed","error":{"message":"boom"}}'
    assert CodexResultParser().parse(stream) is None


def test_parser_returns_none_for_non_json_lines() -> None:
    assert CodexResultParser().parse("not-json\nstill-not-json") is None


def test_parser_returns_none_when_agent_text_is_not_json() -> None:
    stream = '{"type":"item.completed","item":{"type":"agent_message","text":"plain words"}}'
    assert CodexResultParser().parse(stream) is None
