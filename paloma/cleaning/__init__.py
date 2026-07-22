"""Cleaning algorithms (implementations of the ``Cleaner`` protocol).

Importing this package registers the built-in cleaners as a side effect, so
:func:`~paloma.core.cleaner.available_cleaners` and
:func:`~paloma.core.cleaner.create_cleaner` work immediately. Add a new cleaning
algorithm by dropping a module here that defines a ``@register_cleaner`` class
and importing it below.

Layout:

* :mod:`paloma.cleaning.dehazer` — the dehazing *engine* (the merged TESS
  dehazing project).
* :mod:`paloma.cleaning.dehazer_cleaner` — the thin :class:`Cleaner` adapter
  that exposes the engine to the pipeline.
"""

from .dehazer_cleaner import DehazerCleaner

__all__ = ["DehazerCleaner"]
