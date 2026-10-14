"""The pydantic base class every response model derives from."""

from __future__ import annotations

from typing import Any

import pydantic
from pydantic import ConfigDict

__all__ = ["BaseModel"]


class BaseModel(pydantic.BaseModel):
    """Base class of every typed response returned by the SDK.

    * Unknown fields are kept (``extra="allow"``), so a newer gateway never breaks an older SDK;
      read them with ``model.model_extra`` or :meth:`to_dict`.
    * Field names that collide with Python keywords carry a trailing underscore (for example
      ``import_``) and are still populated from, and serialized to, their wire name.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        protected_namespaces=(),
        use_attribute_docstrings=True,
    )

    def to_dict(self, *, exclude_none: bool = False) -> dict[str, Any]:
        """Return the wire-shaped ``dict`` (aliases applied, unknown fields included)."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=exclude_none)

    def to_json(self, *, indent: int | None = None, exclude_none: bool = False) -> str:
        """Return the wire-shaped JSON string (aliases applied, unknown fields included)."""
        return self.model_dump_json(by_alias=True, indent=indent, exclude_none=exclude_none)
