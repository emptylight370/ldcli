from ._version import __version__
from .cli import main

__all__ = ["main", "__version__"]

if __name__ == "__main__":
    raise SystemExit(main())
