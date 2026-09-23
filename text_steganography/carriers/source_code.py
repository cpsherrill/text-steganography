"""A source-code carrier.

For source code the invariant is program behavior, not visible prose. The
channels shipped so far change actual characters, so they can only run where a
changed character cannot change what the program does. That rules out string
literals (a no-break space inside a string changes the string's value) and
inter-token whitespace (a no-break space is not token-separating whitespace to
most compilers, so it would fail to parse). The permitted region is
**ordinary comment contents**: a compiler ignores them, and prose in a comment has real
inter-word spaces to work with.

So this carrier's safe spans are the interiors of comments. It tracks string
literals as it scans, so a ``//`` or ``#`` inside a string is not mistaken for
a comment. Embedding string-representation channels (quote style, escape
equivalence) that could safely use string literals is future work; those are
channels, not a carrier concern.

Constructed per language with :meth:`for_language`, or directly with explicit
comment and string syntax. Serialization stores the explicit syntax, so a
config round-trips regardless of how the carrier was built.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import io
import re
import tokenize

from ..errors import ConfigError

from .base import CarrierAdapter, Span, register_carrier

_PRESETS: Dict[str, Dict[str, object]] = {
    "python": {
        "line_comment": "#",
        "block_open": None,
        "block_close": None,
        "string_delims": ("'", '"'),
        "triple_quote": True,
    },
    "c": {
        "line_comment": "//",
        "block_open": "/*",
        "block_close": "*/",
        "string_delims": ('"', "'"),
        "triple_quote": False,
    },
    "javascript": {
        "line_comment": "//",
        "block_open": "/*",
        "block_close": "*/",
        "string_delims": ('"', "'", "`"),
        "triple_quote": False,
    },
}


@register_carrier
class SourceCodeCarrier(CarrierAdapter):
    id = "carrier.source_code"
    version = "2"

    def __init__(
        self,
        line_comment: Optional[str] = "//",
        block_open: Optional[str] = "/*",
        block_close: Optional[str] = "*/",
        string_delims: Tuple[str, ...] = ('"', "'"),
        triple_quote: bool = False,
    ) -> None:
        self.line_comment = line_comment or None
        self.block_open = block_open or None
        self.block_close = block_close or None
        self.string_delims = tuple(string_delims)
        self.triple_quote = bool(triple_quote)

    @classmethod
    def for_language(cls, language: str) -> "SourceCodeCarrier":
        try:
            preset = _PRESETS[language.lower()]
        except KeyError:
            known = ", ".join(sorted(_PRESETS))
            raise ValueError(f"unknown language {language!r}; known: {known}") from None
        return cls(**preset)  # type: ignore[arg-type]

    def params(self) -> Dict[str, object]:
        return {
            "line_comment": self.line_comment,
            "block_open": self.block_open,
            "block_close": self.block_close,
            "string_delims": list(self.string_delims),
            "triple_quote": self.triple_quote,
        }

    def _skip_string(self, document: str, start: int, quote: str) -> int:
        n = len(document)
        j = start + 1
        while j < n:
            if document[j] == "\\":
                j += 2
                continue
            if document[j] == quote:
                return j + 1
            j += 1
        return n  # unterminated string runs to the end

    def _python_spans(self, document: str) -> List[Span]:
        offsets = [0] + [i + 1 for i, char in enumerate(document) if char == "\n"]
        spans = []
        try:
            for token in tokenize.generate_tokens(io.StringIO(document).readline):
                if token.type == tokenize.ERRORTOKEN and not token.string.isspace():
                    raise ConfigError("malformed Python token; no embedding performed")
                if token.type != tokenize.COMMENT:
                    continue
                # Encoding cookies and executable-file directives are comments
                # to the lexer, but changing them can change program behavior.
                if token.start[0] <= 2 and (
                    token.string.startswith("#!") or re.search(r"coding[:=]", token.string)
                ):
                    continue
                start = offsets[token.start[0] - 1] + token.start[1] + 1
                end = offsets[token.end[0] - 1] + token.end[1]
                if start < end:
                    spans.append((start, end))
        except (tokenize.TokenError, IndentationError, SyntaxError) as error:
            raise ConfigError("cannot tokenize Python source safely") from error
        return spans

    def safe_spans(self, document: str) -> List[Span]:
        if self.params() == SourceCodeCarrier.for_language("python").params():
            return self._python_spans(document)
        if self.triple_quote:
            raise ConfigError("custom triple-quoted syntax requires a language tokenizer")
        # Line splicing changes comment boundaries before C lexical analysis.
        if "\\\n" in document or "\\\r\n" in document:
            raise ConfigError("source line continuations are not supported by this carrier")
        safe: List[Span] = []
        n = len(document)
        i = 0
        while i < n:
            char = document[i]
            if char == "`":
                raise ConfigError("template literals are not supported by this source carrier")
            if char in self.string_delims:
                i = self._skip_string(document, i, char)
                continue
            if self.block_open and self.block_close and document.startswith(self.block_open, i):
                start = i + len(self.block_open)
                close = document.find(self.block_close, start)
                if close == -1:
                    raise ConfigError("unterminated block comment")
                safe.append((start, close))
                i = close + len(self.block_close)
                continue
            if self.line_comment and document.startswith(self.line_comment, i):
                start = i + len(self.line_comment)
                end = document.find("\n", start)
                end = n if end == -1 else end
                safe.append((start, end))
                i = end
                continue
            if char == "/" and "`" in self.string_delims:
                # Distinguishing regexp literals from division needs a full JS
                # grammar. Reject before any edits instead of guessing comments.
                raise ConfigError("JavaScript regexp/division syntax requires a parser; "
                                  "this carrier supports comments and quoted strings only")
            i += 1
        return safe
