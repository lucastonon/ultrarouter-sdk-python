"""Module kinds. A ``kind`` is an opaque label the compiler never branches on; a profile declares
the vocabulary it recognises with :func:`define_kinds`.
"""

from __future__ import annotations

__all__ = ["KindSet", "define_kinds"]


class KindSet:
    """A resolved set of kinds a profile recognises (order preserved, duplicates collapsed)."""

    def __init__(self, kinds: tuple[str, ...]) -> None:
        self.kinds = kinds
        self._set = frozenset(kinds)

    def has(self, value: str) -> bool:
        """Whether ``value`` is one of the kinds."""
        return value in self._set


def define_kinds(kinds: list[str] | tuple[str, ...]) -> KindSet:
    """Build a :class:`KindSet` from ``kinds`` (order kept, duplicates dropped)."""
    unique: list[str] = []
    for value in kinds:
        if value not in unique:
            unique.append(value)
    return KindSet(tuple(unique))
