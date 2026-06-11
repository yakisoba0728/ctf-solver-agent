"""Tests for flag pattern matching."""

from ctf_solver.tools.flag import extract_flags, DEFAULT_FLAG_PATTERN


def test_extract_standard_flag():
    flags = extract_flags("The flag is FLAG{hello_world}", DEFAULT_FLAG_PATTERN)
    assert flags == ["FLAG{hello_world}"]


def test_extract_ctf_flag():
    flags = extract_flags("Found: ctf{secret123}", DEFAULT_FLAG_PATTERN)
    assert flags == ["ctf{secret123}"]


def test_extract_multiple():
    text = "First: FLAG{a}, then flag{b}, also CTF{c}"
    flags = extract_flags(text, DEFAULT_FLAG_PATTERN)
    assert len(flags) == 3


def test_dedup():
    text = "FLAG{same} and FLAG{same} again"
    flags = extract_flags(text, DEFAULT_FLAG_PATTERN)
    assert flags == ["FLAG{same}"]


def test_custom_pattern():
    flags = extract_flags("key: ABC123XYZ", r"ABC\d+XYZ")
    assert flags == ["ABC123XYZ"]


def test_no_match():
    flags = extract_flags("nothing here", DEFAULT_FLAG_PATTERN)
    assert flags == []


def test_nested_braces():
    flags = extract_flags("FLAG{a{b}c}", DEFAULT_FLAG_PATTERN)
    assert len(flags) >= 1
