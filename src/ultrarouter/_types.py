"""Small shared types: the ``NOT_GIVEN`` sentinel."""

from __future__ import annotations

from typing import Any, Final, Literal

from typing_extensions import override

__all__ = ["NOT_GIVEN", "NotGiven", "compact", "is_given"]


class NotGiven:
    """Sentinel for "argument not supplied", distinct from an explicit ``None``.

    Update methods use it for fields the API lets you clear: leaving the argument out sends
    nothing, passing ``None`` sends ``null`` (clearing the value).
    """

    _instance: NotGiven | None = None

    def __new__(cls) -> NotGiven:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> Literal[False]:
        return False

    @override
    def __repr__(self) -> str:
        return "NOT_GIVEN"


#: The single :class:`NotGiven` instance.
NOT_GIVEN: Final = NotGiven()


def is_given(value: object) -> bool:
    """Return ``True`` unless ``value`` is :data:`NOT_GIVEN`."""
    return not isinstance(value, NotGiven)


def compact(**fields: Any) -> dict[str, Any]:
    """Build a request body, dropping ``None`` and :data:`NOT_GIVEN` values."""
    return {k: v for k, v in fields.items() if v is not None and not isinstance(v, NotGiven)}
