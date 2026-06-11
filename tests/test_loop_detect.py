"""Tests for loop detector."""

from ctf_solver.collaboration.loop_detect import LoopDetector


def test_no_loop():
    ld = LoopDetector()
    assert ld.check("bash", "ls") is None
    assert ld.check("bash", "cat file.txt") is None


def test_warn_at_threshold():
    ld = LoopDetector(warn_threshold=3, break_threshold=5)
    assert ld.check("bash", "ls") is None
    assert ld.check("bash", "ls") is None
    assert ld.check("bash", "ls") == "warn"


def test_break_at_threshold():
    ld = LoopDetector(warn_threshold=3, break_threshold=5)
    for _ in range(5):
        result = ld.check("bash", "ls")
    assert result == "break"


def test_reset_clears_history():
    ld = LoopDetector(warn_threshold=3, break_threshold=5)
    for _ in range(4):
        ld.check("bash", "ls")
    ld.reset()
    assert ld.check("bash", "ls") is None


def test_different_args_no_loop():
    ld = LoopDetector()
    for i in range(10):
        assert ld.check("bash", f"cmd {i}") is None


def test_dict_args():
    ld = LoopDetector()
    assert ld.check("bash", {"command": "ls"}) is None
    assert ld.check("bash", {"command": "ls"}) is None
    assert ld.check("bash", {"command": "ls"}) == "warn"
