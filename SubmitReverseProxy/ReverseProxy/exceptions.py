class DBConnectionError(RuntimeError):
    """Raised when there is an error connecting to the database.""" """USED"""

class DBConfigError(RuntimeError):
    """Raised when the database is not configured.""" """USED"""

class AuthError (RuntimeError):
    """Raise when no auth object is present"""

class UnauthorizedError (ValueError):
    """ Raise on unauthorized request """

class DeletedError (ValueError):
    """ Raise on unauthorized request """