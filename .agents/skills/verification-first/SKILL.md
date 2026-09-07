---
name: verification-first
description: Implementation is not completion. A feature is complete only after the intended behavior has been verified.
---

# Verification First

## Principle
Implementation is not completion.
A feature is complete only after the intended behavior has been verified.

## Verification Process
After implementation:

### 1. Verify the happy path
Confirm the primary user flow works.

### 2. Verify expected failure paths
Test relevant failures such as:
- invalid input
- missing authentication
- invalid API key
- provider timeout
- rate limit
- network failure
- empty state

### 3. Check regressions
Confirm related existing functionality still works.

### 4. Verify the actual user experience
Do not only inspect API responses.
For UI features, use the real flow.
For provider features, test a real provider interaction when possible.

## Minimum Verification Report
After meaningful work, report:
- What was implemented
- What was tested
- What passed
- Any known limitation

Do not claim "fully working" without verification.

## Test Priorities
Prioritize tests for:
- authentication
- API key security
- encryption/decryption
- provider adapters
- router behavior
- conversation persistence
- critical user flows

## Anti-patterns
Avoid:
- "It compiles, so it works"
- testing only the happy path
- assuming UI behavior from code inspection
- declaring success without running relevant checks
- fixing one bug without checking nearby functionality

The standard is:
**Evidence before confidence.**
