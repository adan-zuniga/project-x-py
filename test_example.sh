#!/bin/bash

export PROJECT_X_API_KEY="your_api_key"
export PROJECT_X_USERNAME="your_username"
export PROJECT_X_ACCOUNT_NAME="your_account_name"
# export PROJECT_X_ACCOUNT_NAME="S1JUL2315209876"

source .venv/bin/activate

uv run "${@:-test.py}"
