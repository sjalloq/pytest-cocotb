# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

from .session import TestSession

try:
    from ._version import __version__
except ModuleNotFoundError:
    __version__ = "0.0.0.dev0+unknown"

__all__ = ["TestSession", "__version__"]
