"""Tests for the auto-categorization rules.

These check the real logic that decides an item's category from its title:
that known keywords land in the right area, that the first matching rule
wins, and that anything unrecognised falls back to "Other".

Run them with:  uv run pytest
"""

import pytest

from app.categorize import (
    CATEGORY_HEALTH,
    CATEGORY_LIFE,
    CATEGORY_MIND,
    CATEGORY_MUSIC,
    CATEGORY_OTHER,
    CATEGORY_SPIRITUAL,
    categorize,
)


# `parametrize` runs this one test once per (title, expected) pair below —
# a tidy way to check many examples without copy-pasting the test.
@pytest.mark.parametrize(
    "title, expected",
    [
        ("Practice sitar", CATEGORY_MUSIC),
        ("Learn Raga Yaman", CATEGORY_MUSIC),
        ("Gayatri mantra", CATEGORY_SPIRITUAL),
        ("Evening meditation", CATEGORY_SPIRITUAL),
        ("Go for a run", CATEGORY_HEALTH),
        ("Book the dentist", CATEGORY_HEALTH),
        ("Read 20 pages", CATEGORY_MIND),
        ("Study for the exam", CATEGORY_MIND),
        ("Pay the electricity bill", CATEGORY_LIFE),
        ("Email the landlord", CATEGORY_LIFE),
    ],
)
def test_keywords_map_to_expected_category(title, expected):
    assert categorize(title) == expected


def test_unknown_title_falls_back_to_other():
    assert categorize("Water the plants") == CATEGORY_OTHER


def test_matching_is_case_insensitive():
    assert categorize("SITAR practice") == CATEGORY_MUSIC


def test_first_matching_rule_wins():
    # "learn" is a Mind keyword and "raga" is a Music keyword. Music is
    # listed first in the rule map, so Music should win.
    assert categorize("Learn a new raga") == CATEGORY_MUSIC
