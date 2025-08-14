Architecture Overview
=====================

The project-x-py SDK uses a modern async architecture optimized for high-performance trading.

Core Components
---------------

- **TradingSuite**: Unified interface for all trading operations
- **ProjectX Client**: Async HTTP client with connection pooling
- **RealtimeClient**: WebSocket connection manager
- **EventBus**: Centralized event handling system
- **Specialized Managers**: Order, Position, Risk, and Data managers

Design Patterns
---------------

- **Dependency Injection**: Managers receive dependencies rather than creating them
- **Factory Functions**: Async factory methods for proper initialization
- **Protocol-based Design**: Type-safe interfaces using Python protocols
- **Context Managers**: Automatic resource cleanup

See the source code for implementation details.