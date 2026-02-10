#!/usr/bin/env python3
"""
SciToken Generator for GraceDB Client Container

Generates a SciToken signed with the local issuer's private key.
Used as part of the container entrypoint to obtain fresh tokens.
"""

import argparse
import base64
import json
import os
import sys
import time
import uuid
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("Error: cryptography package not installed", file=sys.stderr)
    print("Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)


def base64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def load_private_key(key_path: str):
    """Load an RSA private key from a PEM file."""
    with open(key_path, 'rb') as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )


def get_kid_from_jwks(jwks_path: str) -> str:
    """Extract the key ID from a JWKS file."""
    try:
        with open(jwks_path, 'r') as f:
            jwks = json.load(f)
            if 'keys' in jwks and len(jwks['keys']) > 0:
                return jwks['keys'][0].get('kid', '')
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    return ''


def generate_token(
    issuer: str,
    subject: str,
    scope: str,
    private_key_path: str,
    jwks_path: str = None,
    audience: str = None,
    lifetime: int = 3600,
    kid: str = None
) -> str:
    """Generate a signed SciToken."""

    # Load the private key
    private_key = load_private_key(private_key_path)

    # Get key ID
    if not kid and jwks_path:
        kid = get_kid_from_jwks(jwks_path)
    if not kid:
        kid = f"key-{time.strftime('%Y%m%d')}"

    # Calculate timestamps
    now = int(time.time())
    exp = now + lifetime

    # Create JWT header
    header = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": kid
    }

    # Create JWT payload
    payload = {
        "sub": subject,
        "iss": issuer.rstrip('/'),
        "exp": exp,
        "iat": now,
        "nbf": now,
        "jti": str(uuid.uuid4()),
        "scope": scope,
        "ver": "scitoken:2.0"
    }

    # Add audience if provided
    if audience:
        if ',' in audience:
            payload["aud"] = audience.split(',')
        else:
            payload["aud"] = audience

    # Encode header and payload
    header_b64 = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(',', ':')).encode())

    # Create signing input
    signing_input = f"{header_b64}.{payload_b64}"

    # Sign with RS256
    signature = private_key.sign(
        signing_input.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature_b64 = base64url_encode(signature)

    # Return complete JWT
    return f"{signing_input}.{signature_b64}"


def main():
    parser = argparse.ArgumentParser(
        description='Generate a SciToken for GraceDB authentication'
    )
    parser.add_argument('--issuer', required=True, help='Issuer URL')
    parser.add_argument('--subject', required=True, help='Subject (username)')
    parser.add_argument('--scope', default='gracedb.read', help='Token scope')
    parser.add_argument('--audience', help='Token audience')
    parser.add_argument('--lifetime', type=int, default=3600, help='Token lifetime in seconds')
    parser.add_argument('--key', default='/issuer/keys/scitoken_private.pem', help='Private key path')
    parser.add_argument('--jwks', default='/issuer/keys/scitoken_public.jwks', help='JWKS file path')
    parser.add_argument('--kid', help='Key ID (extracted from JWKS if not provided)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress info messages')

    args = parser.parse_args()

    try:
        token = generate_token(
            issuer=args.issuer,
            subject=args.subject,
            scope=args.scope,
            private_key_path=args.key,
            jwks_path=args.jwks,
            audience=args.audience,
            lifetime=args.lifetime,
            kid=args.kid
        )

        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, 'w') as f:
                f.write(token)
            if not args.quiet:
                print(f"Token written to: {args.output}", file=sys.stderr)
        else:
            print(token)

        if not args.quiet:
            # Decode and print token info
            parts = token.split('.')
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
            print(f"\n{'='*50}", file=sys.stderr)
            print("SciToken Generated Successfully", file=sys.stderr)
            print(f"{'='*50}", file=sys.stderr)
            print(f"Issuer:   {payload['iss']}", file=sys.stderr)
            print(f"Subject:  {payload['sub']}", file=sys.stderr)
            print(f"Scope:    {payload['scope']}", file=sys.stderr)
            print(f"Audience: {payload.get('aud', '(none)')}", file=sys.stderr)
            print(f"Expires:  {time.ctime(payload['exp'])} ({args.lifetime}s)", file=sys.stderr)
            print(f"{'='*50}\n", file=sys.stderr)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating token: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
