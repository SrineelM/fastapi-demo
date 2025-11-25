"""
RSA Key Generation Script

Generates RSA key pairs for JWT RS256 signing.
Use this for production environments.

Usage:
    python scripts/generate_keys.py
"""

import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

def generate_rsa_keys(output_dir: str = "keys") -> tuple[str, str]:
    """
    Generate RSA key pair for JWT signing.
    
    Args:
        output_dir: Directory to store keys
        
    Returns:
        Tuple of (private_key_path, public_key_path)
    """
    # Create keys directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,  # Strong 4096-bit key
        backend=default_backend()
    )
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Extract and serialize public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Write to files
    private_key_path = output_path / "private.pem"
    public_key_path = output_path / "public.pem"
    
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    os.chmod(private_key_path, 0o600)  # Restrict permissions
    
    with open(public_key_path, "wb") as f:
        f.write(public_pem)
    
    print(f"✅ RSA keys generated successfully")
    print(f"   Private key: {private_key_path}")
    print(f"   Public key: {public_key_path}")
    print(f"\n⚠️  IMPORTANT:")
    print(f"   - Keep private.pem SECURE")
    print(f"   - Only share public.pem")
    print(f"   - Store in secure location (secrets manager)")
    
    return str(private_key_path), str(public_key_path)

if __name__ == "__main__":
    generate_rsa_keys()
