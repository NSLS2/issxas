"""X-ray absorption spectroscopy processing for NSLS-II ISS."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("xas")
except PackageNotFoundError:
    __version__ = "0+unknown"
