"""Provides base Exceptions for conversion container."""

class FileTypeError(ValueError):
    """Raised when there is a value error due to incorrect file type."""

class GCPBlobError(RuntimeError):
    """Raised when there is an error with uploading or downloading GCP blobs."""

class TarError(RuntimeError):
    """Raised when the untar operation fails."""

class LaTeXMLRemoveError(RuntimeError):
    """Raised when removing a .ltxml file fails."""

class MainTeXError(RuntimeError):
    """Raised when finding a main .tex file fails or no main .tex file is found."""

class CleanupError(RuntimeError):
    """Raised when removing the .tar.gz object from local memory after conversion is complete fails."""

class PayloadError(RuntimeError):
    """Raised when the Payload is malformed."""
    
class HTMLInjectionError(RuntimeError):
    """Raised when there is an error injecting a HTML tag into the HTML file."""

class UploadError(RuntimeError):
    """Raised when there is a problem uploading the output"""