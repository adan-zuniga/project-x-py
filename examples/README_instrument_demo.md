# Instrument Search Demo

## Overview
The `09_get_check_available_instruments.py` script is an interactive demo that showcases the ProjectX instrument search functionality.

## Features
- **Interactive search**: Enter any futures symbol to search for contracts
- **Smart contract selection**: See how `get_instrument()` selects the best matching contract
- **All contracts view**: Compare all available contracts with `search_instruments()`
- **Visual formatting**: Clear display of contract details with active contract indicators

## Usage
```bash
# Make sure you have environment variables set
export PROJECT_X_API_KEY="your-api-key"
export PROJECT_X_USERNAME="your-username"

# Run the demo
python examples/09_get_check_available_instruments.py
```

## Example Session
```
Enter a symbol to search (or 'quit' to exit): NQ

============================================================
Searching for: 'NQ'
============================================================

1. All contracts matching 'NQ':
--------------------------------------------------
   Found 2 contract(s):

   ★ [1] NQU5 - E-mini NASDAQ-100: September 2025
     [2] MNQU5 - Micro E-mini Nasdaq-100: September 2025

2. Best match using get_instrument('NQ'):
--------------------------------------------------
   Selected: NQU5
   ┌─ Contract Details ─────────────────────────────
   │ ID:           CON.F.US.ENQ.U25
   │ Name:         NQU5
   │ Symbol ID:    F.US.ENQ
   │ Description:  E-mini NASDAQ-100: September 2025
   │ Active:       ✓ Yes
   │ Tick Size:    0.25
   │ Tick Value:   $5.0
   └───────────────────────────────────────────────
```

## Contract Naming
- Contract names include futures month codes + year
- Examples: `NQU5` = NQ + U (September) + 5 (2025)
- Month codes: F(Jan), G(Feb), H(Mar), J(Apr), K(May), M(Jun), N(Jul), Q(Aug), U(Sep), V(Oct), X(Nov), Z(Dec)

## Commands
- **Symbol name**: Search for that symbol (e.g., "ES", "NQ", "CL")
- **help**: Show common symbols table
- **quit/exit/q**: Exit the demo