"""The fmu-settings package."""

try:
    from ._version import version

    __version__ = version
except ImportError:
    __version__ = version = "0.0.0"
