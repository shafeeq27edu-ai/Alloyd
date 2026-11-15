# Privacy Policy — DRAFT

> **DRAFT — OWNER REVIEW REQUIRED.** This text was written by the project's
> coding agent from the actual code and has not been reviewed by the owner or a
> lawyer. It is not legal advice. Bracketed placeholders must be filled in, and
> the draft notes at the end list claims that need a human decision before this
> is shown to anyone else.

**Operator:** [OPERATOR LEGAL NAME]
**Contact:** [CONTACT EMAIL]
**Effective date:** [DATE]

## 1. What this policy covers

This policy describes how [OPERATOR LEGAL NAME] ("we") handles personal data in
Alloyd ("the service"), a chat workspace that sends your prompts to AI providers
using API keys you supply.

## 2. What we store

Alloyd stores only what the application needs to work:

| Data | What it is | Where it lives |
| :--- | :--- | :--- |
| Account | Email address, bcrypt password hash, creation time | Application database |
| Provider keys | Your API keys for Groq, Google Gemini, and/or Anthropic, encrypted with Fernet; a short masked hint | Application database |
| Conversations and messages | The text of your prompts and the models' answers, in plaintext | Application database |
| Usage records | Per provider attempt: provider, model, routing mode, category, success/error status, error code, whether a fallback happened, latency, token counts (provider-reported or estimated), estimated cost. **No prompt or answer text.** | Application database |
| Server logs | Request method, path, status code, duration, request ID; warnings such as fallback events. No bodies, keys, or message content. | [SERVER LOG DESTINATION] |
| Cookies | `access_token` (session) and `csrf_token` (request forgery protection) | Your browser |

We do not use advertising, analytics, or tracking services, and we do not sell
personal data.

## 3. Your API keys and the providers

Keys are encrypted before storage and are never returned to the browser after
you save them, never written to logs, and never shared with another provider.
When you send a message, the backend decrypts the relevant key in memory and
sends it only to that key's provider, together with your prompt and the recent
conversation history, so the provider can answer.

That means Groq, Google, or Anthropic (whichever you chose) receives your
prompt and answer under **their** privacy terms and data-use policies. [OPERATOR
TO CONFIRM LINKS TO EACH PROVIDER'S POLICY.] Alloyd cannot control what a
provider does with data it receives.

Adding or updating a key causes Alloyd to validate it with a lightweight call to
that provider.

## 4. Why we process data

- To create and secure your account and sessions.
- To route, send, and display your conversations.
- To keep your conversation history and usage records for your own use.
- To operate, debug, and secure the service (rate limiting, error diagnosis
  without content).

[OPERATOR TO CONFIRM LEGAL BASIS IF GDPR OR SIMILAR LAW APPLIES.]

## 5. Retention and deletion

- Message content and conversations are kept until you delete the conversation
  or your account.
- Usage records are deleted with their conversation, or with your account.
- Deleting your account in Settings requires your password and permanently
  removes your credentials, provider keys, conversations, messages, and usage
  records. There is no recovery window and no soft delete.
- [OPERATOR TO STATE BACKUP RETENTION. Alloyd's code has no backup feature; if
  the operator takes database backups, those copies need their own retention
  statement.]

## 6. Security

Provider keys are encrypted at rest with a key held by the operator, sessions use
HttpOnly cookies, state-changing requests require a CSRF token and an allowlisted
origin, and every record is filtered by the authenticated account on the server.

Known limits, documented in the project's security notes:

- Conversation content is stored in plaintext; database access control is the
  boundary protecting it.
- There is no multi-factor authentication, email verification, password reset,
  or account lockout beyond rate limits.
- Rate limiting is held in memory per server process.

No system is perfectly secure. [OPERATOR TO STATE BREACH NOTIFICATION
OBLIGATIONS FOR THEIR JURISDICTION.]

## 7. Your choices

You can delete individual conversations, remove a provider key, or delete your
account at any time in Settings. [OPERATOR TO STATE HOW USERS CAN REQUEST
ACCESS, CORRECTION, OR EXPORT, AND THE RESPONSE WINDOW.] Alloyd has no self-serve
data export feature today.

## 8. Children

The service is not intended for anyone under [MINIMUM AGE], and we do not
knowingly collect data from children. [OPERATOR TO SET THE AGE.]

## 9. Changes

If this policy changes materially, [OPERATOR TO STATE HOW USERS ARE NOTIFIED].
The effective date above will change.

## 10. Contact

Questions or requests: [CONTACT EMAIL], [POSTAL ADDRESS IF REQUIRED].

---

## Draft notes for the owner (delete before publishing)

1. Fill every bracket. The operator's legal identity, contact, jurisdiction, and
   minimum age are decisions this draft cannot make.
2. Decide whether the service is offered free to a small group, commercially,
   or internally. That changes the legal basis and consumer-law sections.
3. Name the hosting provider and database location, and whether backups exist.
   The code stores everything in the configured PostgreSQL database, so the
   operator controls location.
4. Add links to the Groq, Google, and Anthropic privacy policies you intend
   users to rely on.
5. A lawyer should review before this is shown to anyone outside the project.
