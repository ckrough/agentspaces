"""Tests for the naming module."""

from __future__ import annotations

import re

import pytest

from agentspaces.infrastructure.naming import (
    ADJECTIVES,
    NOUNS,
    generate_name,
    is_valid_name,
)


class TestGenerateName:
    """Tests for generate_name function."""

    def test_generates_adjective_noun_format(self) -> None:
        """Name should be in adjective-noun format."""
        name = generate_name()
        parts = name.split("-")

        assert len(parts) == 2
        assert parts[0] in ADJECTIVES
        assert parts[1] in NOUNS

    def test_generates_lowercase_names(self) -> None:
        """Names should be all lowercase."""
        name = generate_name()
        assert name == name.lower()

    def test_generates_unique_names_with_check(self) -> None:
        """Should generate unique names when exists_check is provided."""
        seen: set[str] = set()

        def exists_check(name: str) -> bool:
            if name in seen:
                return True
            seen.add(name)
            return False

        # Generate several names, all should be unique
        names = [generate_name(exists_check=exists_check) for _ in range(10)]
        assert len(names) == len(set(names))

    def test_raises_after_max_attempts(self) -> None:
        """Should raise RuntimeError if can't find unique name."""
        # Always return True (name exists)
        def always_exists(_name: str) -> bool:
            return True

        with pytest.raises(RuntimeError, match="Failed to generate unique name"):
            generate_name(exists_check=always_exists, max_attempts=10)

    def test_name_matches_pattern(self) -> None:
        """Name should match expected pattern."""
        name = generate_name()
        # Pattern: lowercase letters with single hyphen
        assert re.match(r"^[a-z]+-[a-z]+$", name)


class TestIsValidName:
    """Tests for is_valid_name function."""

    def test_valid_names(self) -> None:
        """Should accept valid workspace names."""
        assert is_valid_name("eager-turing")
        assert is_valid_name("bold-einstein")
        assert is_valid_name("zen-curie")

    def test_invalid_empty_name(self) -> None:
        """Should reject empty names."""
        assert not is_valid_name("")

    def test_invalid_single_word(self) -> None:
        """Should reject single-word names."""
        assert not is_valid_name("turing")
        assert not is_valid_name("eager")

    def test_invalid_too_many_parts(self) -> None:
        """Should reject names with too many parts."""
        assert not is_valid_name("eager-bold-turing")

    def test_invalid_uppercase(self) -> None:
        """Should reject uppercase names."""
        assert not is_valid_name("Eager-Turing")
        assert not is_valid_name("EAGER-TURING")

    def test_invalid_with_numbers(self) -> None:
        """Should reject names with numbers."""
        assert not is_valid_name("eager-turing1")
        assert not is_valid_name("eager1-turing")

    def test_invalid_with_special_chars(self) -> None:
        """Should reject names with special characters."""
        assert not is_valid_name("eager_turing")
        assert not is_valid_name("eager.turing")


class TestWordLists:
    """Tests for the word lists."""

    def test_adjectives_are_lowercase(self) -> None:
        """All adjectives should be lowercase."""
        for adj in ADJECTIVES:
            assert adj == adj.lower(), f"'{adj}' is not lowercase"

    def test_nouns_are_lowercase(self) -> None:
        """All nouns should be lowercase."""
        for noun in NOUNS:
            assert noun == noun.lower(), f"'{noun}' is not lowercase"

    def test_adjectives_are_unique(self) -> None:
        """Adjectives should be unique."""
        assert len(ADJECTIVES) == len(set(ADJECTIVES))

    def test_nouns_are_unique(self) -> None:
        """Nouns should be unique."""
        assert len(NOUNS) == len(set(NOUNS))

    def test_sufficient_combinations(self) -> None:
        """Should have enough combinations for uniqueness."""
        # At least 1000 possible combinations
        combinations = len(ADJECTIVES) * len(NOUNS)
        assert combinations >= 1000
