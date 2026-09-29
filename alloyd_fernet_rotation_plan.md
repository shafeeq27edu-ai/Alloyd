# Alloyd Fernet Encryption Key Rotation Plan

## 1. Current Encryption Architecture
- **Location:** Encryption and decryption logic is contained in `backend/app/core/encryption.py`.
- **Initialization:** A single `Fernet` instance is initialized globally using `settings.ENCRYPTION_KEY`.
- **Usage:** Used exclusively for encrypting `provider_keys.encrypted_key` in `backend/app/api/keys.py` and decrypting when sending requests via provider adapters.
- **Data Model:** `ProviderKey` (in `models.py`) stores `encrypted_key` as a `String` with no explicit version marker.

## 2. Current Ciphertext Format
- Standard `Fernet` URL-safe base64-encoded string. It natively begins with `g` (byte 0x80) and includes an unencrypted timestamp, IV, ciphertext, and HMAC.

## 3. Rotation Design (Dual-Key Read Compatibility)
The safest approach is leveraging `MultiFernet` from Python's `cryptography.fernet` package, which is designed explicitly for key rotation.
- **Active Key:** The new key used for all *new* encryptions.
- **Previous Key(s):** Fallback keys used *only* for decryption of older ciphertext.
- **Migration:** Read all records. `MultiFernet.decrypt()` will successfully decrypt them if they were encrypted with the old key. Immediately re-encrypt them (which `MultiFernet.encrypt()` natively does with the *new, active key*).

## 4. Key Configuration
Update `backend/app/config.py`:
- `ENCRYPTION_KEY` becomes the **active** key.
- `PREVIOUS_ENCRYPTION_KEY` (Optional) string holding the old key during the rotation window.
- If `PREVIOUS_ENCRYPTION_KEY` is set, `app/core/encryption.py` initializes a `MultiFernet([Fernet(active), Fernet(previous)])`.
- If absent, it initializes a single `Fernet(active)`.

## 5. Migration Algorithm (Management Command)
Create an internal script `backend/scripts/rotate_keys.py`:
1. Load `settings.ENCRYPTION_KEY` and `settings.PREVIOUS_ENCRYPTION_KEY`. Fail if previous key is missing.
2. Initialize `MultiFernet`.
3. Fetch all `ProviderKey` records from the DB in batches.
4. For each record:
    - Decrypt `record.encrypted_key` using `MultiFernet`.
    - Re-encrypt the resulting plaintext using `MultiFernet.encrypt()` (this uses the active key).
    - If the new ciphertext != old ciphertext (meaning it was rotated), stage for commit.
5. Commit to database.
6. Report success/failure counts without exposing credentials.

## 6. Failure Handling & Idempotency
- **Idempotency:** Because `MultiFernet` tries keys sequentially, if a record was already rotated in a previous run, `decrypt()` still works (using the active key), and re-encrypting it simply generates a new valid ciphertext under the active key. It is perfectly safe to run multiple times.
- **Atomicity:** We will use database transactions (either processing all at once or in discrete batches) so partial failures roll back cleanly.

## 7. Concurrency Behavior
- If two rotation scripts run concurrently, they will both decrypt and re-encrypt the same records. Due to Fernet's random IV, the ciphertexts will differ, and the last write wins. Both writes are valid and decryptable by the active key. This is inherently safe.

## 8. Dry-Run Behavior
- Add a `--dry-run` flag to the script.
- In dry-run mode: Decrypt each key, encrypt it, count successes/failures, but do not call `session.commit()`.

## 9. Testing Strategy
- Create `backend/tests/test_encryption_rotation.py`.
- Test encryption/decryption with single key.
- Test `PREVIOUS_ENCRYPTION_KEY` configuration logic.
- Test decryption of old ciphertext using dual-key config.
- Test that new encryption always uses the active key.
- Test the migration script logic using fake keys (`fake-groq-key`).

## 10. Security Properties
- **No Plaintext in DB:** Plaintext only exists in memory during the Python script execution.
- **No Logs:** No values will be printed to stdout, only integer counts.
- **No Exposed API:** The rotation is a local script, not an HTTP endpoint.
- **Eventual Key Deletion:** Once the script succeeds on all records, `PREVIOUS_ENCRYPTION_KEY` can be safely removed from the environment configuration.
