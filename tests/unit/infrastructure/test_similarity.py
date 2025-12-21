"""Tests for string similarity utilities."""

from __future__ import annotations

from agentspaces.infrastructure.similarity import (
    find_similar_names,
    levenshtein_distance,
)


class TestLevenshteinDistance:
    """Tests for levenshtein_distance function."""

    def test_identical_strings_return_zero(self) -> None:
        """Identical strings should have distance 0."""
        assert levenshtein_distance("hello", "hello") == 0

    def test_empty_strings_return_zero(self) -> None:
        """Two empty strings should have distance 0."""
        assert levenshtein_distance("", "") == 0

    def test_one_empty_string(self) -> None:
        """Distance to empty string is length of other string."""
        assert levenshtein_distance("hello", "") == 5
        assert levenshtein_distance("", "world") == 5

    def test_single_insertion(self) -> None:
        """Single character difference should be distance 1."""
        assert levenshtein_distance("cat", "cats") == 1

    def test_single_deletion(self) -> None:
        """Single deletion should be distance 1."""
        assert levenshtein_distance("cats", "cat") == 1

    def test_single_substitution(self) -> None:
        """Single substitution should be distance 1."""
        assert levenshtein_distance("cat", "bat") == 1

    def test_multiple_operations(self) -> None:
        """Multiple operations should sum correctly."""
        # "kitten" -> "sitting" requires 3 operations:
        # k->s, e->i, +g
        assert levenshtein_distance("kitten", "sitting") == 3

    def test_completely_different_strings(self) -> None:
        """Completely different strings of same length."""
        assert levenshtein_distance("abc", "xyz") == 3

    def test_case_sensitive(self) -> None:
        """Distance should be case-sensitive."""
        assert levenshtein_distance("Hello", "hello") == 1

    def test_symmetric(self) -> None:
        """Distance should be symmetric."""
        assert levenshtein_distance("abc", "def") == levenshtein_distance("def", "abc")


class TestFindSimilarNames:
    """Tests for find_similar_names function."""

    def test_empty_candidates_returns_empty(self) -> None:
        """Empty candidate list should return empty list."""
        result = find_similar_names("test", [])
        assert result == []

    def test_exact_match_included(self) -> None:
        """Exact matches should be included."""
        candidates = ["eager-turing", "happy-hopper", "wise-wozniak"]
        result = find_similar_names("eager-turing", candidates)
        assert "eager-turing" in result

    def test_similar_names_found(self) -> None:
        """Should find names with small edit distance."""
        candidates = ["eager-turing", "eager-touring", "happy-hopper"]
        result = find_similar_names("eager-turingg", candidates)
        assert "eager-turing" in result

    def test_respects_max_distance(self) -> None:
        """Should not return names exceeding max_distance."""
        candidates = ["abc", "xyz"]
        result = find_similar_names("abc", candidates, max_distance=1)
        assert "abc" in result
        assert "xyz" not in result

    def test_respects_max_suggestions(self) -> None:
        """Should limit number of suggestions."""
        candidates = ["aaa", "aab", "aac", "aad", "aae"]
        result = find_similar_names("aaa", candidates, max_suggestions=2)
        assert len(result) <= 2

    def test_sorted_by_distance(self) -> None:
        """Results should be sorted by distance (closest first)."""
        candidates = ["abc", "abcd", "abcde"]
        result = find_similar_names("abc", candidates)
        # "abc" is distance 0, "abcd" is distance 1, "abcde" is distance 2
        assert result[0] == "abc"
        if len(result) > 1:
            assert result[1] == "abcd"

    def test_case_insensitive_matching(self) -> None:
        """Matching should be case-insensitive."""
        candidates = ["Eager-Turing", "happy-hopper"]
        result = find_similar_names("eager-turing", candidates)
        assert "Eager-Turing" in result

    def test_default_max_distance_is_three(self) -> None:
        """Default max_distance should be 3."""
        candidates = ["abcdef"]
        # "abc" to "abcdef" is distance 3, should be included
        result = find_similar_names("abc", candidates)
        assert "abcdef" in result

        # "ab" to "abcdef" is distance 4, should not be included
        result = find_similar_names("ab", candidates)
        assert "abcdef" not in result

    def test_alphabetical_tiebreaker(self) -> None:
        """Names with same distance should be sorted alphabetically."""
        candidates = ["ccc", "aaa", "bbb"]
        result = find_similar_names("ddd", candidates)
        # All have distance 3, should be sorted alphabetically
        assert result == ["aaa", "bbb", "ccc"]
