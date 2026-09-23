#!/usr/bin/env python3
# coding: utf-8
"""A small report helper with literal words in its documentation."""
from dataclasses import dataclass


@dataclass
class Entry:
    name: str
    value: int


def summarize(entries):
    # Keep input order so that duplicate names stay in the report.
    prefix = "# a string, not a comment"
    raw = r"a backslash \\ and literal words"
    # Render the total without changing the original records.
    return f"{prefix}: {sum(item.value for item in entries)}", raw
