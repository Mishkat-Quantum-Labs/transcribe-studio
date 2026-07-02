import os

from app.process import (
    clear_pid_file,
    ensure_can_start,
    pid_file_path,
    read_pid_file,
    running_instance,
    write_pid_file,
)


def test_pid_file_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRIBE_STUDIO_DATA", str(tmp_path))
    clear_pid_file()
    write_pid_file("127.0.0.1", 8082)
    info = read_pid_file()
    assert info is not None
    assert info["pid"] == str(os.getpid())
    assert info["port"] == "8082"
    clear_pid_file()
    assert pid_file_path().exists() is False


def test_ensure_can_start_blocks_duplicate(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRIBE_STUDIO_DATA", str(tmp_path))
    clear_pid_file()
    write_pid_file("127.0.0.1", 8082)
    try:
        ensure_can_start("127.0.0.1", 8082, force=False)
        assert False, "should exit"
    except SystemExit as exc:
        assert exc.code == 1
    finally:
        clear_pid_file()