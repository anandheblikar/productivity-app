"""Auto-categorization: turn an item's title into a category.

The user never picks or manages categories. When an item is added, this
module reads its title and assigns one category using a simple map of
keywords. Categories exist only to power the weekly review ("what did my
life get this week, by area").

Everything lives in one obvious place — the ``CATEGORY_RULES`` list below —
so adding a new keyword is a one-line change. Smarter sorting (e.g. AI) is
a later upgrade.
"""

# The five "real" categories plus the Other catch-all.
# The emoji are used as little labels in the UI (Everything / This week).
CATEGORY_MUSIC = "Music"
CATEGORY_SPIRITUAL = "Spiritual"
CATEGORY_HEALTH = "Health"
CATEGORY_MIND = "Mind"
CATEGORY_LIFE = "Life stuff"
CATEGORY_OTHER = "Other"

# The order categories appear in grouped lists (Everything, This week).
CATEGORY_ORDER = [
    CATEGORY_MUSIC,
    CATEGORY_SPIRITUAL,
    CATEGORY_HEALTH,
    CATEGORY_MIND,
    CATEGORY_LIFE,
    CATEGORY_OTHER,
]

# A small emoji for each category, for the headings in the UI.
CATEGORY_EMOJI = {
    CATEGORY_MUSIC: "🎵",
    CATEGORY_SPIRITUAL: "🕉️",
    CATEGORY_HEALTH: "💪",
    CATEGORY_MIND: "🧠",
    CATEGORY_LIFE: "🏠",
    CATEGORY_OTHER: "•",
}

# The rule map. Each entry is (category, [keywords]). We check them in
# order and the first category with a matching keyword wins. To teach the
# app a new word, just add it to the right list here.
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    (CATEGORY_MUSIC, ["sitar", "raga", "music", "sing", "guitar", "tabla", "riyaz"]),
    (CATEGORY_SPIRITUAL, ["mantra", "pray", "prayer", "meditate", "meditation", "gayatri", "chant", "godly"]),
    (CATEGORY_HEALTH, ["run", "gym", "exercise", "workout", "stretch", "walk", "yoga", "dentist", "doctor", "weight", "kg"]),
    (CATEGORY_MIND, ["read", "learn", "code", "study", "write", "book", "course", "python", "git"]),
    (CATEGORY_LIFE, ["bill", "buy", "email", "call", "clean", "pay", "book the", "errand", "groceries", "house", "family", "friend", "cook"]),
]


def categorize(title: str) -> str:
    """Return the best category for an item title.

    We lowercase the title and look for any rule keyword inside it. The
    first rule (in ``CATEGORY_RULES`` order) that matches wins. If nothing
    matches, we fall back to ``Other``.

    Examples:
        categorize("Practice sitar")      -> "Music"
        categorize("Gayatri mantra")      -> "Spiritual"
        categorize("Book the dentist")    -> "Health"
        categorize("Water the plants")    -> "Other"
    """
    text = title.lower()
    for category, keywords in CATEGORY_RULES:
        for keyword in keywords:
            if keyword in text:
                return category
    return CATEGORY_OTHER
