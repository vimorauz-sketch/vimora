"""Allowlisted AI capabilities.

The executor can ONLY produce files of the declared output types for a capability. It cannot
run shell commands, call arbitrary tools, read other customers' data, or access secrets. Code
is generated as text and, if sandbox validation is enabled, checked in an isolated container.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    key: str
    description: str
    output_extensions: tuple[str, ...]
    max_files: int = 5
    max_file_bytes: int = 400_000
    validators: tuple[str, ...] = field(default_factory=tuple)
    reads_text_inputs: bool = True


CAPABILITIES: dict[str, Capability] = {
    "document_writing": Capability("document_writing", "Write or edit text documents: articles, letters, descriptions, CVs, business texts.", ("md", "txt"), validators=("non_empty", "min_length")),
    "translation": Capability("translation", "Translate supplied text between Uzbek, English and Russian (and other languages).", ("md", "txt"), validators=("non_empty", "min_length")),
    "data_transformation": Capability("data_transformation", "Clean, restructure or convert supplied tabular/JSON data into CSV or JSON.", ("csv", "json"), validators=("non_empty", "csv_or_json_parses")),
    "code_generation": Capability("code_generation", "Write source code (scripts, bots, small programs). Code is NOT executed on the platform.", ("py", "js", "ts", "html", "css", "json", "md", "txt", "sql", "sh", "yml", "yaml"),
                                  max_files=12, validators=("non_empty", "python_syntax", "json_parses", "sandbox_python")),
    "summarization": Capability("summarization", "Summarize or analyze supplied documents and produce a written report.", ("md", "txt"), validators=("non_empty", "min_length")),
}

TEXT_INPUT_MIME = {"text/plain", "text/markdown", "text/csv", "application/csv", "application/json"}
MAX_INPUT_CHARS = 60_000


def get_capability(key: str | None) -> Capability | None:
    return CAPABILITIES.get(key or "")
