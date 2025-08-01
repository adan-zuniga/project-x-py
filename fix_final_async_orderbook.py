#!/usr/bin/env python3
"""Final fix for async orderbook syntax errors."""

# Read the current file
with open("src/project_x_py/async_orderbook.py") as f:
    lines = f.readlines()

# Find the broken detect_iceberg_orders method and fix it
output_lines = []
in_broken_method = False

for i, line in enumerate(lines):
    if "async def detect_iceberg_orders(" in line:
        # Start of the method - add it properly
        output_lines.append(line)
        in_broken_method = True
    elif in_broken_method and line.strip().startswith("async def add_callback"):
        # End of broken method, start of next method
        # Add the missing _trigger_callbacks method first
        output_lines.extend(
            [
                "\n",
                "    async def _trigger_callbacks(self, event_type: str, data: dict[str, Any]) -> None:\n",
                '        """Trigger all callbacks for a specific event type."""\n',
                "        for callback in self.callbacks.get(event_type, []):\n",
                "            try:\n",
                "                if asyncio.iscoroutinefunction(callback):\n",
                "                    await callback(data)\n",
                "                else:\n",
                "                    callback(data)\n",
                "            except Exception as e:\n",
                '                self.logger.error(f"Error in {event_type} callback: {e}")\n',
                "\n",
            ]
        )
        in_broken_method = False
        output_lines.append(line)
    elif in_broken_method:
        # Skip broken method content - we'll replace it
        continue
    else:
        output_lines.append(line)

# Write the fixed file
with open("src/project_x_py/async_orderbook.py", "w") as f:
    f.writelines(output_lines)

print("✅ Fixed final async orderbook syntax errors")
