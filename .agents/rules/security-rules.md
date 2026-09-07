# Security Rules

Security is not a final polish step.
It is part of every feature.

## API Keys

API keys must:
- be encrypted before database storage
- never be stored in plaintext
- never be logged
- never appear in error messages
- never be committed to Git
- never be returned by APIs
- never be exposed to client-side JavaScript
- only be decrypted immediately before making a provider request

Database compromise alone should not expose provider keys.

## Logging

Never log:
- API keys
- authorization headers
- session tokens
- encryption keys
- full secret-bearing request bodies
- provider credentials

Logs should contain enough information for debugging without exposing secrets.

## Error Responses

Never expose:
- Python stack traces
- provider internal errors
- database errors
- environment configuration
- secret values

The user should receive a clear, actionable message.
The internal system may log a sanitized technical error.
