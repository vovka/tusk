from demos.editor_emulator.emulated_editor import EmulatedEditor


def test_select_all_copy_exposes_buffer_on_clipboard() -> None:
    editor = EmulatedEditor()
    editor.write_clipboard("function hi() {}")
    editor.press_keys("<ctrl>a")
    editor.press_keys("<ctrl>v")
    editor.press_keys("<ctrl>a")
    editor.press_keys("<ctrl>c")
    assert editor.clipboard == "function hi() {}"
    assert editor.buffer == "function hi() {}"


def test_paste_over_select_all_replaces_whole_buffer() -> None:
    editor = EmulatedEditor()
    editor.type_text("old content")
    editor.press_keys("<ctrl>a")
    editor.write_clipboard("new content")
    editor.press_keys("<ctrl>v")
    assert editor.buffer == "new content"


def test_clipboard_restore_does_not_touch_buffer() -> None:
    editor = EmulatedEditor()
    editor.type_text("buffer text")
    editor.write_clipboard("saved clipboard")
    assert editor.buffer == "buffer text"
    assert editor.clipboard == "saved clipboard"


def test_other_keys_drop_selection_so_paste_appends() -> None:
    editor = EmulatedEditor()
    editor.type_text("line one")
    editor.press_keys("<ctrl>a")
    editor.press_keys("Home")
    editor.write_clipboard("!")
    editor.press_keys("<ctrl>v")
    assert editor.buffer == "line one!"
