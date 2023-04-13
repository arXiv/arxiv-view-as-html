class FileTypeError(ValueError):
    pass

class GCPBlobError(RuntimeError):
    pass

class TarError(RuntimeError):
    pass

class LaTeXMLRemoveError(RuntimeError):
    pass

class MainTeXError(RuntimeError):
    pass

class CleanupError(RuntimeError):
    pass

class PayloadError(RuntimeError):
    pass