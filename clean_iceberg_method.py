#!/usr/bin/env python3
"""Clean up the broken iceberg method."""

# Read the file
with open("src/project_x_py/async_orderbook.py") as f:
    lines = f.readlines()

# Find the broken part starting at line 1001
# Remove everything from line 1001 to the next valid method
output_lines = []
skip = False
for i, line in enumerate(lines):
    if i == 1000:  # Line 1001 (0-indexed)
        skip = True
    elif skip and line.strip().startswith("async def add_callback"):
        skip = False

    if not skip:
        output_lines.append(line)

# Write back
with open("src/project_x_py/async_orderbook.py", "w") as f:
    f.writelines(output_lines)

print("✅ Cleaned up broken iceberg method implementation")
