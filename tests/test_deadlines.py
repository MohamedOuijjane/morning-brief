"""Today is Monday 16 November 2026 (see conftest)."""

from datetime import date

import pytest

from brief import config, deadlines


def test_window_includes_today_to_fourteen_days() -> None:
    text = deadlines.get_deadlines()
    assert "Past item" not in text
    assert "Item &lt;today&gt;" in text  # HTML-escaped
    assert "Item in 14 days" in text
    assert "Item too far" not in text


def test_entries_are_sorted_with_labels() -> None:
    lines = deadlines.get_deadlines().splitlines()
    assert lines[0] == "📅 <b>Échéances (14 prochains jours)</b>"
    assert lines[1] == "🔴 Item &lt;today&gt; : lun. 16 nov. (AUJOURD'HUI)"
    assert lines[2] == "🔴 Item tomorrow : mar. 17 nov. (demain)"
    assert lines[3] == "🟡 Item in 4 days : ven. 20 nov. (dans 4 jours)"
    assert lines[-1] == "🟢 Item in 14 days : lun. 30 nov. (dans 14 jours)"


@pytest.mark.parametrize(
    ("days", "label", "marker"),
    [(0, "AUJOURD'HUI", "🔴"), (1, "demain", "🔴"), (2, "dans 2 jours", "🔴"),
     (7, "dans 7 jours", "🟡"), (8, "dans 8 jours", "🟢")],
)
def test_labels_and_urgency(days: int, label: str, marker: str) -> None:
    assert deadlines.when_label(days) == label
    assert deadlines.urgency_marker(days) == marker


def test_window_size_is_configurable(monkeypatch) -> None:
    monkeypatch.setattr(config, "DEADLINES_DAYS", 1)
    text = deadlines.get_deadlines()
    assert "Item tomorrow" in text and "Item in 4 days" not in text


def test_nothing_due(monkeypatch) -> None:
    monkeypatch.setattr(config, "DEADLINES_JSON", '[{"title": "x", "date": "2030-01-01"}]')
    assert deadlines.get_deadlines().endswith("Rien à signaler. 🎉")


def test_no_source_skips_the_sections(monkeypatch) -> None:
    monkeypatch.setattr(config, "DEADLINES_JSON", "")
    assert deadlines.get_deadlines() is None
    assert deadlines.get_tomorrow_deadlines() is None


def test_local_file_is_used_without_secret(monkeypatch, tmp_path) -> None:
    local = tmp_path / "deadlines.json"
    local.write_text('[{"title": "From file", "date": "2026-11-18"}]')
    monkeypatch.setattr(config, "DEADLINES_JSON", "")
    monkeypatch.setattr(config, "DEADLINES_FILE", str(local))
    assert "From file" in deadlines.get_deadlines()


def test_tomorrow_deadlines() -> None:
    assert deadlines.get_tomorrow_deadlines() == "⏰ <b>À rendre demain</b>\n• Item tomorrow"


def test_tomorrow_section_omitted_when_nothing_due(freeze) -> None:
    freeze("2026-11-21T20:00:00")
    assert deadlines.get_tomorrow_deadlines() is None


def test_deadlines_between_is_inclusive_and_sorted() -> None:
    due = deadlines.deadlines_between(date(2026, 11, 17), date(2026, 11, 26))
    assert [d.day for d, _ in due] == [17, 20, 26]
