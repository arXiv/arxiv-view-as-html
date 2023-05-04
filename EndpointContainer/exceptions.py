"""Provides base Exceptions for Endpoint container."""

class FileTypeError(ValueError):
    """Raised when there is a value error due to incorrect file type."""

class GCPBlobError(RuntimeError):
    """Raised when there is an error with uploading or downloading GCP blobs.""" """USED"""

class TarError(RuntimeError):
    """Raised when the untar operation fails.""" """USED"""

class LaTeXMLRemoveError(RuntimeError):
    """Raised when removing a .ltxml file fails."""

class CleanupError(RuntimeError):
    """Raised when removing the .tar.gz object from local memory after conversion is complete fails."""

class PayloadError(RuntimeError):
    """Raised when the Payload is malformed."""

class HTMLInjectionError(RuntimeError):
    """Raised when there is an error injecting a HTML tag into the HTML file.""" """USED"""

class DBConnectionError(RuntimeError):
    """Raised when there is an error connecting to the database.""" """USED"""

class DBConfigError(RuntimeError):
    """Raised when the database is not configured.""" """USED"""
    