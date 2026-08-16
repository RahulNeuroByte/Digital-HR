from app.ingestion.cleaner import clean_text


def test_collapses_excess_whitespace():
    raw = "Hello    world\t\ttest"
    assert clean_text(raw) == "Hello world test"


def test_collapses_excess_blank_lines():
    raw = "Line one\n\n\n\n\nLine two"
    cleaned = clean_text(raw)
    assert "\n\n\n" not in cleaned
    assert "Line one" in cleaned and "Line two" in cleaned


def test_empty_input_returns_empty():
    assert clean_text("") == ""
    assert clean_text(None) == ""  # type: ignore[arg-type]
