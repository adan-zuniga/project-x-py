#!/bin/bash
# Deploy versioned documentation using Mike

set -e

# Check if version argument provided
if [ $# -eq 0 ]; then
    echo "Usage: ./scripts/deploy-docs.sh <version> [alias]"
    echo "Example: ./scripts/deploy-docs.sh 3.3.4 latest"
    exit 1
fi

VERSION=$1
ALIAS=${2:-""}

echo "Building and deploying documentation for version $VERSION"

# Install dependencies if needed
pip install mike mkdocs mkdocs-material mkdocstrings[python]

# Deploy the version
if [ -n "$ALIAS" ]; then
    echo "Deploying with alias: $ALIAS"
    mike deploy --push --update-aliases $VERSION $ALIAS
else
    mike deploy --push $VERSION
fi

# Set default version if this is the latest
if [ "$ALIAS" = "latest" ]; then
    mike set-default --push latest
fi

echo "Documentation deployed successfully!"
echo "View all versions with: mike list"
