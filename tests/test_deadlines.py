"""Today is Monday 16 November 2026 (see conftest)."""

from datetime import date

import pytest

from brief import config, deadlines


def test_window_includes_today_to_fourteen_days() -> None:
    text = deadlines.get_deadlines()
    assert "Rendu passé" not in text  # yesterday
    assert "Rapport &lt;final&gt;" in text  # today, HTML-escaped
    assert "Mémoire intermédiaire" in text  # exactly 14 days
    assert "Trop loin" not in text  # 15 days


def test_entries_are_sorted_with_labels() -> None:
    lines = deadlines.get_deadlines().splitlines()
    assert lines[0] == "📅 <b>Échéances (14 prochains jours)</b>"
    assert lines[1] == "🔴 Rapport &lt;final&gt; : lun. 16 nov. (AUJOURD'HUI)"
    assert lines[2] == "🔴 Exposé de groupe : mar. 17 nov. (demain)"
    assert lines[3] == "🟡 Quiz chapitre 3 : ven. 20 nov. (dans 4 jours)"
    assert lines[-1] == "🟢 Mémoire intermédiaire : lun. 30 nov. (dans 14 jours)"


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
    assert "(1 prochains jours)" in text
    assert "Exposé de groupe" in text and "Quiz chapitre 3" not in text


def test_nothing_due(monkeypatch) -> None:
    monkeypatch.setattr(config, "DEADLINES_JSON", '[{"title": "x", "date": "2030-01-01"}]')
    assert deadlines.get_deadlines().endswith("Rien à signaler. 🎉")


def test_secret_takes_priority_over_files(monkeypatch) -> None:
    secret = '[{"title": "Depuis le secret", "date": "2026-11-18"}]'
    monkeypatch.setattr(config, "DEADLINES_JSON", secret)
    text = deadlines.get_deadlines()
    assert "Depuis le secret" in text and "Quiz" not in text


def test_no_source_at_all_means_no_deadlines(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config, "DEADLINES_FILE", str(tmp_path / "none.json"))
    monkeypatch.setattr(config, "DEADLINES_FALLBACK_FILE", str(tmp_path / "none2.json"))
    assert deadlines.load_deadlines() == []


def test_tomorrow_deadlines() -> None:
    assert deadlines.get_tomorrow_deadlines() == "⏰ <b>À rendre demain</b>\n• Exposé de groupe"


def test_tomorrow_section_omitted_when_empty(freeze) -> None:
    freeze("2026-11-21T20:00:00")  # nothing due on the 22nd
    assert deadlines.get_tomorrow_deadlines() is None


def test_deadlines_between_is_inclusive_and_sorted() -> None:
    due = deadlines.deadlines_between(date(2026, 11, 17), date(2026, 11, 26))
    assert [d.day for d, _ in due] == [17, 20, 26]
