"""Compatibility entry point for the registered Fleet Lab service."""

import sys

sys.dont_write_bytecode = True

from pihti.server import app


__all__ = ["app"]
