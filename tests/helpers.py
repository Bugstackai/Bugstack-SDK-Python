"""Shared test helpers."""


def make_exception(msg="test error", exc_type=ValueError):
    """Create an exception with a traceback."""
    try:
        raise exc_type(msg)
    except exc_type as e:
        return e
