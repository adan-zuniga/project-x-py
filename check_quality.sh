#!/bin/bash
# Code Quality Check Script for ProjectX SDK
# This script must pass completely for any code to be considered complete

set -e  # Exit on first error

echo "========================================="
echo "ProjectX SDK Code Quality Checks"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
FAILED=0

# 1. Format Check
echo -e "\n${YELLOW}[1/7] Checking code formatting...${NC}"
if uv run ruff format --check .; then
    echo -e "${GREEN}✓ Code formatting check passed${NC}"
else
    echo -e "${RED}✗ Code formatting issues found. Run: uv run ruff format .${NC}"
    FAILED=1
fi

# 2. Linting
echo -e "\n${YELLOW}[2/7] Running linter...${NC}"
if uv run ruff check .; then
    echo -e "${GREEN}✓ Linting passed${NC}"
else
    echo -e "${RED}✗ Linting errors found. Run: uv run ruff check . --fix${NC}"
    FAILED=1
fi

# 3. Type Checking
echo -e "\n${YELLOW}[3/7] Running type checker...${NC}"
if uv run mypy src/; then
    echo -e "${GREEN}✓ Type checking passed${NC}"
else
    echo -e "${RED}✗ Type errors found${NC}"
    FAILED=1
fi

# 4. Security Scan
echo -e "\n${YELLOW}[4/7] Running security scan...${NC}"
if uv run bandit -r src/ -ll; then
    echo -e "${GREEN}✓ Security scan passed${NC}"
else
    echo -e "${RED}✗ Security issues found${NC}"
    FAILED=1
fi

# 5. Complexity Check
echo -e "\n${YELLOW}[5/7] Checking code complexity...${NC}"
COMPLEXITY_OUTPUT=$(uv run radon cc src/ -s -n B 2>&1 || true)
if [ -z "$COMPLEXITY_OUTPUT" ]; then
    echo -e "${GREEN}✓ Complexity check passed (all functions below B rating)${NC}"
else
    echo -e "${RED}✗ Complex functions found (B rating or worse):${NC}"
    echo "$COMPLEXITY_OUTPUT"
    FAILED=1
fi

# 6. Check for TODOs/FIXMEs
echo -e "\n${YELLOW}[6/7] Checking for TODO/FIXME comments...${NC}"
TODO_COUNT=$(grep -r "TODO\|FIXME\|XXX\|HACK" src/ --include="*.py" 2>/dev/null | wc -l || echo "0")
if [ "$TODO_COUNT" -eq "0" ]; then
    echo -e "${GREEN}✓ No TODO/FIXME comments found${NC}"
else
    echo -e "${RED}✗ Found $TODO_COUNT TODO/FIXME comments:${NC}"
    grep -r "TODO\|FIXME\|XXX\|HACK" src/ --include="*.py" -n | head -10
    FAILED=1
fi

# 7. Check for type: ignore and noqa
echo -e "\n${YELLOW}[7/7] Checking for suppressed warnings...${NC}"
IGNORE_COUNT=$(grep -r "type:\s*ignore\|noqa\|pragma:\s*no cover\|pylint:\s*disable" src/ --include="*.py" 2>/dev/null | wc -l || echo "0")
if [ "$IGNORE_COUNT" -eq "0" ]; then
    echo -e "${GREEN}✓ No suppressed warnings found${NC}"
else
    echo -e "${YELLOW}⚠ Found $IGNORE_COUNT suppressed warnings (should be fixed for v4.0):${NC}"
    grep -r "type:\s*ignore\|noqa" src/ --include="*.py" -n | head -5
    # Don't fail for now, but this should be zero for v4.0
fi

# Summary
echo -e "\n========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL QUALITY CHECKS PASSED!${NC}"
    echo "========================================="
    exit 0
else
    echo -e "${RED}✗ QUALITY CHECKS FAILED!${NC}"
    echo -e "${RED}Code does not meet quality standards.${NC}"
    echo -e "${RED}Fix all issues before considering task complete.${NC}"
    echo "========================================="
    exit 1
fi
