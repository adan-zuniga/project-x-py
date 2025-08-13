# Release Notes - v3.1.11

## 🎯 Risk Manager Market Price Fetching Fix

### Overview
This release fixes a critical issue in the Risk Manager's ManagedTrade class where the `_get_market_price()` method was not implemented, preventing users from entering risk-managed trades without explicitly providing an entry price.

### What's Fixed

#### ManagedTrade Market Price Implementation
- **Problem**: When using `ManagedTrade.enter_long()` or `enter_short()` without an explicit `entry_price`, the system would fail with `NotImplementedError`
- **Solution**: Fully implemented `_get_market_price()` method that fetches current market prices from the data manager
- **Impact**: Risk-managed trades can now be entered using current market prices automatically

### Technical Details

#### Implementation Features
- **Smart Timeframe Fallback**: Tries multiple timeframes in order (1sec → 15sec → 1min → 5min) to get the most recent price
- **Direct Price Access**: Falls back to `get_current_price()` if bar data isn't available
- **Data Manager Integration**: ManagedTrade now receives data manager from TradingSuite automatically
- **Clear Error Messages**: Provides helpful error messages when market price cannot be fetched

#### Code Changes
```python
# Before (would fail)
async with suite.managed_trade(max_risk_percent=0.01) as trade:
    result = await trade.enter_long(
        stop_loss=current_price - 50,  # Would throw NotImplementedError
        take_profit=current_price + 100
    )

# After (works perfectly)
async with suite.managed_trade(max_risk_percent=0.01) as trade:
    result = await trade.enter_long(
        stop_loss=current_price - 50,  # Automatically fetches market price
        take_profit=current_price + 100
    )
```

### Migration Guide
No breaking changes. Existing code will continue to work. The enhancement is backward compatible:
- If you provide `entry_price` explicitly, it works as before
- If you omit `entry_price`, the system now fetches it automatically

### Testing
The implementation has been tested with live market data:
- ✅ Market price fetching works correctly
- ✅ Fallback through multiple timeframes functions properly
- ✅ Integration with TradingSuite is seamless
- ✅ Risk orders (stop loss, take profit) are properly attached

### Dependencies
No new dependencies required. Uses existing data manager infrastructure.

### Known Issues
None at this time.

### Future Improvements
- Consider adding configurable timeframe priority for price fetching
- Add option to use bid/ask prices instead of last trade price
- Implement price staleness checks with configurable thresholds

### Support
For issues or questions about this release, please open an issue on GitHub or contact support.

---
*Released: 2025-08-13*  
*Version: 3.1.11*  
*Type: Bug Fix / Feature Enhancement*