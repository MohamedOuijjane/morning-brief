from datetime import date

import pytest

from brief import config, utils


def test_long_date_in_french() -> None:
    assert utils.format_long_date(date(2026, 11, 16)) == "lundi 16 novembre 2026"
    assert utils.format_long_date(date(2027, 8, 1)) == "dimanche 1 août 2027"


def test_short_date_in_french() -> None:
    assert utils.format_short_date(date(2026, 11, 17)) == "mar. 17 nov."
    assert utils.format_short_date(date(2027, 2, 5)) == "ven. 5 févr."
    assert utils.format_short_date(date(2026, 12, 31)) == "jeu. 31 déc."


@pytest.mark.parametrize("month", range(1, 13))
def test_every_month_has_a_french_name(month: int) -> None:
    d = date(2026, month, 1)
    assert utils.MONTHS[month - 1] in utils.format_long_date(d)
    assert utils.MONTHS_SHORT[month - 1] in utils.format_short_date(d)


def test_french_numbers_and_plural() -> None:
    assert utils.fr_number(10.9) == "10,9"
    assert utils.fr_number(12) == "12"
    assert utils.plural(1, "échéance") == "1 échéance"
    assert utils.plural(0, "événement") == "0 événement"
    assert utils.plural(3, "événement") == "3 événements"


def test_escape_html() -> None:
    assert utils.escape("A & <B>") == "A &amp; &lt;B&gt;"


def test_today_uses_configured_timezone(freeze, monkeypatch) -> None:
    freeze("2026-11-16T23:30:00+00:00")
    monkeypatch.setattr(config, "TIMEZONE", "Europe/Paris")  # UTC+1: already the 17th
    assert utils.today() == date(2026, 11, 17)
    monkeypatch.setattr(config, "TIMEZONE", "Europe/London")  # UTC+0: still the 16th
    assert utils.today() == date(2026, 11, 16)


def test_load_json_priority(tmp_path) -> None:
    local = tmp_path / "local.json"
    fallback = tmp_path / "fallback.json"
    fallback.write_text('["fallback"]')
    assert utils.load_json("", str(local), str(fallback)) == ["fallback"]
    local.write_text('["local"]')
    assert utils.load_json("", str(local), str(fallback)) == ["local"]
    assert utils.load_json('["secret"]', str(local), str(fallback)) == ["secret"]


def test_load_json_without_any_source(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        utils.load_json("", str(tmp_path / "missing.json"))


def test_pick_by_date_is_stable_and_cycles() -> None:
    items = ["a", "b", "c"]
    d = date(2026, 11, 16)
    assert utils.pick_by_date(items, d) == utils.pick_by_date(items, d)
    picks = {utils.pick_by_date(items, date.fromordinal(d.toordinal() + i)) for i in range(3)}
    assert picks == set(items)
