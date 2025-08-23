#!/bin/bash
# Serve MkDocs documentation locally

echo "Starting MkDocs server..."
echo "Documentation will be available at http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Serve the documentation
mkdocs serve --dev-addr localhost:8000
