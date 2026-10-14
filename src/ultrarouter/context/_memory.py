"""Memory classes. The core four are a closed vocabulary; a profile may extend them with
:func:`define_memory_classes`. The compiler never branches on a memory class.
"""

from __future__ import annotations

__all__ = ["CORE_MEMORY_CLASSES", "MemoryClassSet", "define_memory_classes"]

CORE_MEMORY_CLASSES: tuple[str, ...] = ("working", "episodic", "semantic", "procedural")


class MemoryClassSet:
    """A resolved set of admissible memory classes for one profile."""

    def __init__(self, classes: tuple[str, ...]) -> None:
        self.classes = classes
        self._set = frozenset(classes)

    def has(self, value: str) -> bool:
        """Whether ``value`` is one of the memory classes."""
        return value in self._set


def define_memory_classes(extra: list[str] | tuple[str, ...] = ()) -> MemoryClassSet:
    """The four core memory classes plus ``extra`` (order kept, duplicates dropped)."""
    classes: list[str] = list(CORE_MEMORY_CLASSES)
    for value in extra:
        if value not in classes:
            classes.append(value)
    return MemoryClassSet(tuple(classes))
