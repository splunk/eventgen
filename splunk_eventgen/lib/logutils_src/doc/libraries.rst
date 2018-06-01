Configuring Libraries
=====================

When developing libraries, you'll probably need to use the
:class:`~logutils.NullHandler` class.

**N.B.** This is part of the standard library since Python 2.7 / 3.1, so the
version here is for use with earlier Python versions.

Typical usage::

    import logging
    try:
        from logging import NullHandler
    except ImportError:
        from logutils import NullHandler

     # use this in all your library's subpackages/submodules
    logger = logging.getLogger(__name__)

    # use this just in your library's top-level package
    logger.addHandler(NullHandler())

.. autoclass:: logutils.NullHandler
   :members:
