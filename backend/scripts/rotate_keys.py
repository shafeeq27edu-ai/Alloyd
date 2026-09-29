import argparse
import sys
import os

# Add the backend directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import ProviderKey
from app.core.encryption import _cipher_suite
from app.config import settings

async def rotate_keys(dry_run: bool = False):
    print("Starting key rotation migration...")
    if not settings.PREVIOUS_ENCRYPTION_KEY:
        print("Error: PREVIOUS_ENCRYPTION_KEY is not set. Cannot perform rotation.")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(ProviderKey))
            keys = result.scalars().all()
            success_count = 0
            skipped_count = 0
            error_count = 0
            
            for key in keys:
                try:
                    # Decrypting with MultiFernet will try all keys in order
                    plaintext = _cipher_suite.decrypt(key.encrypted_key.encode('utf-8'))
                    
                    # Encrypting will always use the active key (the first in the list)
                    new_ciphertext = _cipher_suite.encrypt(plaintext).decode('utf-8')
                    
                    if new_ciphertext != key.encrypted_key:
                        key.encrypted_key = new_ciphertext
                        success_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    error_count += 1
                    # Log without exposing credentials or ciphertexts
                    print(f"Error rotating key ID {key.id}")

            print(f"Rotation results:")
            print(f"  - Rotated: {success_count}")
            print(f"  - Skipped (already rotated): {skipped_count}")
            print(f"  - Errors: {error_count}")
            
            if dry_run:
                print("Dry run complete. No changes committed to the database.")
                await db.rollback()
            else:
                if error_count == 0:
                    await db.commit()
                    print("Changes committed to the database.")
                else:
                    await db.rollback()
                    print("Errors encountered. Rolling back changes.")
                    sys.exit(1)
                    
        except Exception as e:
            print(f"Error connecting to database: {e}")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate encryption keys for provider API keys.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without committing changes.")
    args = parser.parse_args()
    
    asyncio.run(rotate_keys(dry_run=args.dry_run))
