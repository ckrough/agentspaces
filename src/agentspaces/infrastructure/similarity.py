"""String similarity utilities for fuzzy matching."""

from __future__ import annotations

__all__ = [
    "find_similar_names",
    "levenshtein_distance",
]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein (edit) distance between two strings.

    The Levenshtein distance is the minimum number of single-character
    edits (insertions, deletions, substitutions) to transform s1 into s2.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        The edit distance between the strings.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    # Use two rows instead of full matrix for space efficiency
    previous_row = list(range(len(s2) + 1))

    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost is 0 if characters match, 1 otherwise
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_similar_names(
    target: str,
    candidates: list[str],
    *,
    max_distance: int = 3,
    max_suggestions: int = 3,
) -> list[str]:
    """Find similar names from a list of candidates.

    Uses Levenshtein distance to find strings similar to the target.

    Args:
        target: The string to match against.
        candidates: List of possible matches.
        max_distance: Maximum edit distance to consider a match.
        max_suggestions: Maximum number of suggestions to return.

    Returns:
        List of similar names, ordered by distance (closest first).
    """
    if not candidates:
        return []

    # Calculate distances and filter by max_distance
    scored = [
        (name, levenshtein_distance(target.lower(), name.lower()))
        for name in candidates
    ]
    within_threshold = [(name, dist) for name, dist in scored if dist <= max_distance]

    # Sort by distance, then alphabetically for ties
    within_threshold.sort(key=lambda x: (x[1], x[0].lower()))

    return [name for name, _ in within_threshold[:max_suggestions]]
