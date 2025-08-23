# Statistics & Analytics API

Comprehensive async-first statistics system with health monitoring and performance tracking (v3.3.0+).

## Overview

The statistics system provides centralized collection and analysis of performance metrics across all SDK components. Features include:

- **100% Async Architecture**: All statistics methods use async/await for optimal performance
- **Multi-format Export**: JSON, Prometheus, CSV, and Datadog formats with data sanitization
- **Component-Specific Tracking**: Enhanced statistics for all managers with specialized metrics
- **Health Monitoring**: Intelligent 0-100 health scoring with configurable thresholds
- **Performance Optimization**: TTL caching, parallel collection, and circular buffers
- **Memory Efficiency**: Circular buffers and lock-free reads for frequently accessed metrics

## Core Components

### StatisticsAggregator


### HealthMonitor


### BaseStatisticsTracker


### StatisticsCollector


## TradingSuite Statistics

### Getting Statistics

```python
from project_x_py import TradingSuite

async def get_comprehensive_statistics():
    suite = await TradingSuite.create("MNQ")

    # Get comprehensive system statistics (async-first API)
    stats = await suite.get_stats()

    # Health scoring (0-100) with intelligent monitoring
    print(f"System Health: {stats['health_score']:.1f}/100")

    # Performance metrics with enhanced tracking
    print(f"API Calls: {stats['total_api_calls']}")
    print(f"Success Rate: {stats['api_success_rate']:.1%}")
    print(f"Memory Usage: {stats['memory_usage_mb']:.1f} MB")

    await suite.disconnect()
```

### Component-Specific Statistics

```python
async def component_statistics():
    suite = await TradingSuite.create("MNQ")

    # Component-specific statistics (all async for consistency)
    order_stats = await suite.orders.get_stats()
    print(f"Fill Rate: {order_stats['fill_rate']:.1%}")
    print(f"Average Fill Time: {order_stats['avg_fill_time_ms']:.0f}ms")

    position_stats = await suite.positions.get_stats()
    print(f"Win Rate: {position_stats.get('win_rate', 0):.1%}")

    # OrderBook statistics (if enabled)
    if suite.orderbook:
        orderbook_stats = await suite.orderbook.get_stats()
        print(f"Depth Updates: {orderbook_stats['depth_updates']}")

    await suite.disconnect()
```

## Export Capabilities

### Multi-format Export

```python
async def export_statistics():
    suite = await TradingSuite.create("MNQ")

    # Multi-format export capabilities
    prometheus_metrics = await suite.export_stats("prometheus")
    csv_data = await suite.export_stats("csv")
    datadog_metrics = await suite.export_stats("datadog")
    json_data = await suite.export_stats("json")

    # Save to files
    with open("metrics.prom", "w") as f:
        f.write(prometheus_metrics)

    with open("stats.csv", "w") as f:
        f.write(csv_data)

    await suite.disconnect()
```

## Health Monitoring

### Real-time Health Scoring

```python
async def monitor_health():
    suite = await TradingSuite.create("MNQ")

    # Real-time health monitoring with degradation detection
    health_score = await suite.get_health_score()
    if health_score < 70:
        print("⚠️ System health degraded - check components")

        # Get detailed component health
        component_health = await suite.get_component_health()
        for name, health in component_health.items():
            if health['error_count'] > 0:
                print(f"  {name}: {health['error_count']} errors")

    await suite.disconnect()
```

### Health Thresholds

```python
from project_x_py.statistics.health import HealthThresholds, HealthMonitor

async def custom_health_monitoring():
    # Configure custom health thresholds
    thresholds = HealthThresholds(
        error_rate_warning=1.0,    # 1% error rate warning
        error_rate_critical=5.0,   # 5% error rate critical
        response_time_warning=500, # 500ms response time warning
        memory_usage_warning=80.0  # 80% memory usage warning
    )

    # Custom category weights
    weights = {
        "errors": 0.30,         # Emphasize error tracking
        "performance": 0.25,    # Performance is critical
        "connection": 0.20,     # Connection stability
        "resources": 0.15,      # Resource usage
        "data_quality": 0.10,   # Data quality
    }

    # Initialize custom health monitor
    monitor = HealthMonitor(thresholds=thresholds, weights=weights)

    # Use with aggregator
    suite = await TradingSuite.create("MNQ")
    stats = await suite.get_stats()
    health_score = await monitor.calculate_health(stats)

    print(f"Custom Health Score: {health_score:.1f}/100")

    await suite.disconnect()
```

## Data Types

### Statistics Types









### Health Types


## Performance Considerations

### Caching Strategy

The statistics system uses TTL caching to optimize performance:

- **Default TTL**: 5 seconds for expensive operations
- **Parallel Collection**: Components collected concurrently using asyncio.gather()
- **Timeout Protection**: 1 second timeout per component prevents hanging
- **Graceful Degradation**: Partial results returned if some components fail

### Memory Management

- **Circular Buffers**: Error history limited to 100 entries per component
- **Bounded Statistics**: Maximum limits prevent memory exhaustion
- **Lock-free Reads**: Frequently accessed metrics use atomic operations
- **Automatic Cleanup**: Old data cleaned up based on configurable parameters

## Best Practices

1. **Monitor Health Regularly**: Check health scores to detect issues early
2. **Use Appropriate Export Formats**: Prometheus for monitoring, CSV for analysis
3. **Configure Thresholds**: Adjust health thresholds based on your environment
4. **Handle Degradation**: Implement alerts for health score drops
5. **Regular Exports**: Export statistics periodically for historical analysis

## Example: Production Monitoring

```python
import asyncio
from project_x_py import TradingSuite

async def production_monitoring():
    """Complete production monitoring example."""
    suite = await TradingSuite.create(
        "MNQ",
        features=["orderbook", "risk_manager"]
    )

    # Run monitoring loop
    while True:
        try:
            # Get comprehensive statistics
            stats = await suite.get_stats()

            # Check system health
            health = stats.get('health_score', 0)
            if health < 80:
                print(f"⚠️ Health Alert: {health:.1f}/100")

                # Get component breakdown
                component_health = await suite.get_component_health()
                for name, metrics in component_health.items():
                    if metrics['error_count'] > 5:
                        print(f"  {name}: {metrics['error_count']} errors")

            # Export metrics for monitoring system
            prometheus_data = await suite.export_stats("prometheus")

            # Save to monitoring endpoint (example)
            # await send_to_monitoring_system(prometheus_data)

            # Performance metrics
            print(f"API Success Rate: {stats.get('api_success_rate', 0):.1%}")
            print(f"Memory Usage: {stats.get('memory_usage_mb', 0):.1f} MB")

            # Wait before next check
            await asyncio.sleep(30)  # Check every 30 seconds

        except Exception as e:
            print(f"Monitoring error: {e}")
            await asyncio.sleep(60)  # Longer wait on error

# Run monitoring
asyncio.run(production_monitoring())
```

## Integration Examples

### Prometheus Integration

```python
async def prometheus_integration():
    suite = await TradingSuite.create("MNQ")

    # Export Prometheus metrics
    metrics = await suite.export_stats("prometheus")

    # Example Prometheus metrics format:
    # # HELP projectx_api_calls_total Total API calls
    # # TYPE projectx_api_calls_total counter
    # projectx_api_calls_total 1234
    #
    # # HELP projectx_health_score Current health score
    # # TYPE projectx_health_score gauge
    # projectx_health_score 85.5

    # Send to Prometheus pushgateway
    # requests.post('http://pushgateway:9091/metrics/job/projectx',
    #               data=metrics)

    await suite.disconnect()
```

### Datadog Integration

```python
async def datadog_integration():
    suite = await TradingSuite.create("MNQ")

    # Export Datadog-compatible metrics
    metrics = await suite.export_stats("datadog")

    # Example: Send to Datadog (requires datadog library)
    # from datadog import api
    #
    # for metric in metrics:
    #     api.Metric.send(
    #         metric='projectx.health_score',
    #         points=metric['value'],
    #         tags=['environment:production']
    #     )

    await suite.disconnect()
```

### CSV Analytics

```python
async def csv_analytics():
    suite = await TradingSuite.create("MNQ")

    # Export CSV for analytics
    csv_data = await suite.export_stats("csv")

    # Save for analysis
    with open("trading_stats.csv", "w") as f:
        f.write(csv_data)

    # Example: Load with pandas for analysis
    # import pandas as pd
    # df = pd.read_csv("trading_stats.csv")
    # print(df.describe())

    await suite.disconnect()
```

## Troubleshooting

### Common Issues

**High Error Rates**
: Check component error counts and logs for specific issues.

**Low Health Scores**
: Review individual component health metrics to identify bottlenecks.

**Memory Usage Spikes**
: Monitor circular buffer sizes and cleanup frequencies.

**Slow Statistics Collection**
: Check network connectivity and component response times.

### Debugging

```python
async def debug_statistics():
    suite = await TradingSuite.create("MNQ")

    # Enable debug logging
    import logging
    logging.getLogger("project_x_py.statistics").setLevel(logging.DEBUG)

    # Get raw component statistics
    for component_name in ["orders", "positions", "data"]:
        if hasattr(suite, component_name):
            component = getattr(suite, component_name)
            if hasattr(component, "get_stats"):
                stats = await component.get_stats()
                print(f"{component_name}: {stats}")

    await suite.disconnect()
```

## Examples

The repository includes comprehensive examples demonstrating the statistics system:

- **20_statistics_usage.py** - Complete statistics system demonstration
- **24_bounded_statistics_demo.py** - Memory-bounded statistics with limits
- **19_risk_manager_live_demo.py** - Risk manager statistics in action
- **22_circuit_breaker_protection.py** - Health monitoring with circuit breakers

## See Also

- [Trading Suite](trading-suite.md) - Main entry point for statistics
- [Order Manager](order-manager.md) - Order management statistics
- [Position Manager](position-manager.md) - Position tracking statistics
- [Data Manager](data-manager.md) - Real-time data statistics
- [Order Book](../guide/orderbook.md) - Level 2 orderbook statistics
