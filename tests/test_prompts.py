"""Tests for prompts.py."""

from ctf_solver.prompts import ChallengeMeta, _rewrite_connection_info, build_prompt, list_distfiles


def test_rewrite_localhost():
    assert "host.docker.internal" in _rewrite_connection_info("nc localhost 1337")


def test_rewrite_127():
    assert "host.docker.internal" in _rewrite_connection_info("nc 127.0.0.1 1337")


def test_rewrite_passthrough():
    assert _rewrite_connection_info("nc example.com 1337") == "nc example.com 1337"


def test_rewrite_empty():
    assert _rewrite_connection_info("") == ""


def test_build_prompt_basic():
    meta = ChallengeMeta(name="test", category="pwn", value=100, description="solve me")
    prompt = build_prompt(meta, [])
    assert "test" in prompt
    assert "pwn" in prompt
    assert "solve me" in prompt


def test_build_prompt_with_hints():
    meta = ChallengeMeta(name="test", description="x", hints=["check headers"])
    prompt = build_prompt(meta, [], hint="look at cookies")
    assert "check headers" in prompt
    assert "look at cookies" in prompt


def test_build_prompt_with_distfiles():
    meta = ChallengeMeta(name="test", description="x")
    prompt = build_prompt(meta, ["chall.bin", "image.png"])
    assert "chall.bin" in prompt
    assert "IMAGE" in prompt


def test_build_prompt_with_connection():
    meta = ChallengeMeta(name="test", description="x", connection_info="nc localhost 9999")
    prompt = build_prompt(meta, [])
    assert "host.docker.internal" in prompt


def test_list_distfiles(tmp_path):
    dist = tmp_path / "distfiles"
    dist.mkdir()
    (dist / "a.txt").write_text("hi")
    (dist / "b.py").write_text("code")
    files = list_distfiles(str(tmp_path))
    assert "a.txt" in files
    assert "b.py" in files


def test_list_distfiles_no_dir(tmp_path):
    assert list_distfiles(str(tmp_path)) == []
