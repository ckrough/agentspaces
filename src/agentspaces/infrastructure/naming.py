"""Docker-style random name generator for workspaces."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "ADJECTIVES",
    "NOUNS",
    "generate_name",
    "is_valid_name",
]

# Adjectives inspired by Docker's name generator
ADJECTIVES: tuple[str, ...] = (
    "admiring",
    "adoring",
    "agitated",
    "amazing",
    "angry",
    "awesome",
    "bold",
    "brave",
    "clever",
    "compassionate",
    "condescending",
    "confident",
    "cranky",
    "dazzling",
    "determined",
    "distracted",
    "dreamy",
    "eager",
    "ecstatic",
    "elastic",
    "elated",
    "elegant",
    "eloquent",
    "epic",
    "fervent",
    "festive",
    "focused",
    "friendly",
    "frosty",
    "funny",
    "gallant",
    "gifted",
    "goofy",
    "gracious",
    "happy",
    "hopeful",
    "hungry",
    "infallible",
    "inspiring",
    "intelligent",
    "jolly",
    "jovial",
    "keen",
    "kind",
    "laughing",
    "loving",
    "lucid",
    "magical",
    "modest",
    "mystifying",
    "naughty",
    "nervous",
    "nice",
    "nifty",
    "nostalgic",
    "objective",
    "optimistic",
    "peaceful",
    "pedantic",
    "pensive",
    "practical",
    "priceless",
    "quirky",
    "quizzical",
    "relaxed",
    "reverent",
    "romantic",
    "serene",
    "sharp",
    "silly",
    "sleepy",
    "stoic",
    "strange",
    "stupefied",
    "suspicious",
    "sweet",
    "tender",
    "thirsty",
    "trusting",
    "upbeat",
    "vibrant",
    "vigilant",
    "vigorous",
    "wizardly",
    "wonderful",
    "xenodochial",
    "youthful",
    "zealous",
    "zen",
)

# Famous scientists and inventors
NOUNS: tuple[str, ...] = (
    "albattani",
    "allen",
    "archimedes",
    "babbage",
    "banach",
    "bardeen",
    "bartik",
    "bell",
    "blackwell",
    "bohr",
    "booth",
    "brown",
    "carson",
    "clarke",
    "curie",
    "darwin",
    "davinci",
    "dijkstra",
    "einstein",
    "engelbart",
    "euclid",
    "euler",
    "fermat",
    "fermi",
    "feynman",
    "franklin",
    "galileo",
    "gates",
    "goldberg",
    "hamilton",
    "hawking",
    "heisenberg",
    "hopper",
    "hugle",
    "hypatia",
    "johnson",
    "joliot",
    "kalam",
    "keller",
    "khorana",
    "kilby",
    "knuth",
    "lalande",
    "lamarr",
    "leakey",
    "lovelace",
    "lumiere",
    "mayer",
    "mccarthy",
    "mcclintock",
    "meitner",
    "mendel",
    "mestorf",
    "morse",
    "murdock",
    "newton",
    "nightingale",
    "nobel",
    "noether",
    "pasteur",
    "payne",
    "perlman",
    "pike",
    "poincare",
    "ptolemy",
    "raman",
    "ride",
    "ritchie",
    "rosalind",
    "saha",
    "sammet",
    "shaw",
    "sinoussi",
    "snyder",
    "stallman",
    "stonebraker",
    "swanson",
    "tesla",
    "thompson",
    "torvalds",
    "turing",
    "villani",
    "volhard",
    "wiles",
    "wilson",
    "wozniak",
    "wright",
    "yonath",
)


def generate_name(
    *,
    exists_check: Callable[[str], bool] | None = None,
    max_attempts: int = 100,
) -> str:
    """Generate a random Docker-style workspace name.

    Format: adjective-noun (e.g., "eager-turing", "bold-einstein")

    Args:
        exists_check: Optional function to check if name already exists.
                     Should return True if name exists (and we need another).
        max_attempts: Maximum attempts to find unique name.

    Returns:
        A unique workspace name.

    Raises:
        RuntimeError: If unable to generate unique name after max_attempts.
    """
    for _ in range(max_attempts):
        adjective = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        name = f"{adjective}-{noun}"

        if exists_check is None or not exists_check(name):
            return name

    msg = f"Failed to generate unique name after {max_attempts} attempts"
    raise RuntimeError(msg)


def is_valid_name(name: str) -> bool:
    """Check if a name follows the workspace naming convention.

    Args:
        name: Name to validate.

    Returns:
        True if valid workspace name format.
    """
    if not name:
        return False

    parts = name.split("-")
    if len(parts) != 2:
        return False

    # Check it matches our format (lowercase, no special chars)
    return all(part.isalpha() and part.islower() for part in parts)
