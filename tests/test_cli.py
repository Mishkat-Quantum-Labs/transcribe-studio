from app.cli import build_parser, default_port


def test_parser_defaults():
    args = build_parser().parse_args([])
    assert args.command == "start"
    assert args.host == "127.0.0.1"
    assert args.port == 8082
    assert args.force is False


def test_parser_port_shorthand():
    args = build_parser().parse_args(["-p", "9000"])
    assert args.command == "start"
    assert args.port == 9000


def test_parser_explicit_stop():
    args = build_parser().parse_args(["stop"])
    assert args.command == "stop"


def test_parser_start_with_flags():
    args = build_parser().parse_args(["start", "--host", "0.0.0.0", "-p", "80", "-f"])
    assert args.command == "start"
    assert args.host == "0.0.0.0"
    assert args.port == 80
    assert args.force is True


def test_parser_env_defaults(monkeypatch):
    monkeypatch.setenv("TRANSCRIBE_STUDIO_HOST", "0.0.0.0")
    monkeypatch.setenv("TRANSCRIBE_STUDIO_PORT", "80")
    args = build_parser().parse_args([])
    assert args.host == "0.0.0.0"
    assert args.port == 80


def test_help_includes_foreground():
    parser = build_parser()
    help_text = parser.format_help()
    assert "--port" in help_text
    assert "--host" in help_text
    assert "foreground" in help_text.lower()
    assert "stop" in help_text