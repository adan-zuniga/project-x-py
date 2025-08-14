Debugging Guide
===============

Tools and techniques for debugging trading applications.

Logging
-------

Enable debug logging::

    from project_x_py import setup_logging
    setup_logging(level='DEBUG')

Performance Monitoring
----------------------

Check performance stats::

    stats = await client.get_performance_stats()
    memory = suite.data.get_memory_stats()

See the source code for additional debugging utilities.