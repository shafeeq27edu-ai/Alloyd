---
name: security-review
description: Security-sensitive changes require an explicit review before completion.
---

# Security Review

## Purpose
Alloyd handles sensitive provider API keys.
Security-sensitive changes require an explicit review before completion.

## Review Checklist

### Secrets
Confirm:
- secrets are never logged
- secrets are never returned in API responses
- secrets are never stored in plaintext
- secrets are not exposed to client-side code
- secrets are not committed to source control

### API Keys
Confirm:
- encryption occurs before database storage
- encrypted values use the established project pattern
- decryption happens only server-side
- decrypted keys exist only for the provider request lifecycle
- provider keys are isolated by user ownership

### Authentication
Confirm:
- protected endpoints require authentication
- users cannot access another user's resources
- session/token validation is enforced
- expired sessions are handled safely
- authentication failures return appropriate responses

### Error Handling
Confirm:
- stack traces are not exposed
- provider errors are sanitized
- database errors are sanitized
- secret values cannot appear in error output

### Data Access
Confirm:
- user-owned resources are scoped by authenticated user ID
- IDs alone cannot bypass ownership checks
- database queries enforce ownership boundaries

## Completion Requirement
For security-sensitive work, explicitly state:
- what security risks were checked
- whether secrets can leak through logs or responses
- whether authorization boundaries were verified

Security should be reviewed before declaring the change complete.
