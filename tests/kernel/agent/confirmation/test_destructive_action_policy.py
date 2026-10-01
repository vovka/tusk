from tusk.kernel.agent.confirmation.destructive_action_policy import DestructiveActionPolicy


def test_close_window_is_destructive() -> None:
    assert DestructiveActionPolicy().describe("gnome.close_window", {"window_title": "Code"}) == "Close window"


def test_delete_and_close_keys_are_destructive() -> None:
    policy = DestructiveActionPolicy()
    for keys in ("Delete", "<ctrl>a+BackSpace", "<alt>F4", "<ctrl>w", "<ctrl>q"):
        assert policy.describe("gnome.press_keys", {"keys": keys}) is not None


def test_harmless_keys_are_not_destructive() -> None:
    policy = DestructiveActionPolicy()
    assert policy.describe("gnome.press_keys", {"keys": "<ctrl>v"}) is None
    assert policy.describe("gnome.press_keys", {"keys": "<ctrl>a"}) is None


def test_shell_kill_and_delete_tools_are_destructive() -> None:
    policy = DestructiveActionPolicy()
    for name in ("run_shell_command", "x.kill_process", "files.delete_file", "execute_shell"):
        assert policy.describe(name, {}) is not None


def test_ordinary_tools_are_not_destructive() -> None:
    assert DestructiveActionPolicy().describe("gnome.focus_window", {"window_title": "Code"}) is None


def test_plus_style_close_keys_are_destructive() -> None:
    # E2E: the agent sent {"keys": "Ctrl+W"}, which slipped past the <ctrl>w spelling and closed a gedit tab
    policy = DestructiveActionPolicy()
    for keys in ("Ctrl+W", "ctrl+q", "Alt+F4", "control+w", "ctrl + w"):
        assert policy.describe("gnome.press_keys", {"keys": keys}) is not None


def test_plus_style_harmless_keys_are_not_destructive() -> None:
    policy = DestructiveActionPolicy()
    for keys in ("Ctrl+V", "ctrl+a", "Ctrl+Shift+T", "w"):
        assert policy.describe("gnome.press_keys", {"keys": keys}) is None
