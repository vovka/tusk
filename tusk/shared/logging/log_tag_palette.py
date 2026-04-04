__all__ = ["color_for", "content_style_for", "group_names", "is_always_visible", "label_for"]

_COLORS = {
    "USER": "\033[90m",
    "READY": "\033[92m",
    "DETECTOR": "\033[33m",
    "TRANSCRIBER": "\033[32m",
    "SANITIZER": "\033[34m",
    "BUFFER": "\033[95m",
    "GATEKEEPER": "\033[36m",
    "GATERECOVERY": "\033[96m",
    "KERNELINPUT": "\033[37m",
    "LLMREQUEST": "\033[34m",
    "LLMPAYLOAD": "\033[94m",
    "LLMTOOLS": "\033[94m",
    "LLMRESPONSE": "\033[36m",
    "LLMWAIT": "\033[37m",
    "AGENT": "\033[97m",
    "TOOL": "\033[35m",
    "PIPELINE": "\033[37m",
    "DICTATION": "\033[96m",
    "ERROR": "\033[31m",
}
_DISPLAY = {
    "LLMREQUEST": "LLMREQ ",
    "LLMPAYLOAD": "LLMPYLD",
    "LLMTOOLS": "LLMTOOL",
    "LLMRESPONSE": "LLMRESP",
    "TRANSCRIBER": "TRNSCRB",
    "SANITIZER": "SANITZR",
    "DICTATION": "DICTATN",
    "DETECTOR": "DETECTR",
}
_CONTENT = {
    "ERROR": "\033[31m",
    "KERNELINPUT": "\033[1m",
    "TUSK": "\033[1m",
}
_GROUPS = {"READY": "ready", "KERNELINPUT": "kernel-input", "LLMREQUEST": "llm-request", "LLMPAYLOAD": "llm-payload", "LLMTOOLS": "llm-tools", "LLMRESPONSE": "llm-response", "LLMWAIT": "llm-wait"}
_ALWAYS = frozenset({"ERROR", "READY", "KERNELINPUT", "TUSK"})


def color_for(tag: str) -> str:
    return _COLORS.get(tag, "\033[0m")


def label_for(tag: str) -> str:
    return _DISPLAY.get(tag, tag[:7].ljust(7))


def content_style_for(tag: str) -> str:
    return _CONTENT.get(tag, "\033[90m")


def group_names(tag: str, group: str | None) -> set[str]:
    names = {tag.casefold()}
    if tag in _GROUPS:
        names.add(_GROUPS[tag])
    if group:
        names.add(group)
    return names


def is_always_visible(tag: str) -> bool:
    return tag in _ALWAYS
