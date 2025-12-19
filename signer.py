#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GXD Script Signer & Integrity Tool
Copyright (C) 2025 @hejhdiss (Muhammed Shafin p)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Author: @hejhdiss (Muhammed Shafin p)
License: GPL-3.0
"""

import os
import sys
import json
import hashlib
import argparse
import base64

SIGNATURE_MARKER = b"\n# --- GXD DIGITAL SIGNATURE START ---\n"
SIGNATURE_END = b"\n# --- GXD DIGITAL SIGNATURE END ---"

def calculate_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        content = f.read()
        if SIGNATURE_MARKER in content:
            content = content.split(SIGNATURE_MARKER)[0]
        hasher.update(content)
    return hasher.hexdigest(), content

def sign_file(target_file, author, license_name):
    if not os.path.exists(target_file):
        print(f"[-] Error: File {target_file} not found.")
        return

    script_hash, original_content = calculate_file_hash(target_file)
    
    metadata = {
        "author": author,
        "license": license_name,
        "timestamp": os.path.getmtime(target_file),
        "integrity_hash": script_hash
    }
    
    encoded_meta = base64.b64encode(json.dumps(metadata).encode()).decode()
    
    signature_block = (
        SIGNATURE_MARKER +
        f"# META: {encoded_meta}\n".encode() +
        f"# SIGNED_BY: {author}\n".encode() +
        SIGNATURE_END
    )

    with open(target_file, 'wb') as f:
        f.write(original_content.strip() if isinstance(original_content, bytes) else original_content.strip().encode())
        f.write(signature_block)

    print(f"[+] Successfully signed {target_file}")
    print(f"[+] Author: {author}")
    print(f"[+] Hash: {script_hash}")

def verify_file(target_file):
    if not os.path.exists(target_file):
        print(f"[-] Error: File {target_file} not found.")
        return

    with open(target_file, 'rb') as f:
        content = f.read()

    if SIGNATURE_MARKER not in content:
        print("[-] Verification Failed: No GXD signature found.")
        return

    parts = content.split(SIGNATURE_MARKER)
    original_part = parts[0].strip()
    signature_part = parts[1]

    try:
        for line in signature_part.decode().split('\n'):
            if line.startswith("# META: "):
                encoded_meta = line.replace("# META: ", "").strip()
                metadata = json.loads(base64.b64decode(encoded_meta).decode())
                break
        else:
            raise ValueError("Metadata line missing")
    except Exception as e:
        print(f"[-] Verification Failed: Signature block is corrupt. ({e})")
        return

    current_hash = hashlib.sha256(original_part).hexdigest()

    print(f"[*] Analyzing: {target_file}")
    print(f"[*] Author: {metadata.get('author')}")
    print(f"[*] License: {metadata.get('license')}")
    
    if current_hash == metadata.get('integrity_hash'):
        print("[+ SUCCESS] Integrity Verified: The code has NOT been modified.")
    else:
        print("[- DANGER] Integrity Check Failed: The code has been tampered with!")
        print(f"    Expected: {metadata.get('integrity_hash')}")
        print(f"    Actual:   {current_hash}")

def main():
    # Define a clean description and epilog
    description = "GXD Script Signer & Integrity Tool"
    epilog = """
Copyright (C) 2025 @hejhdiss (Muhammed Shafin p)
License: GPL-3.0
Author's GitHub: https://github.com/hejhdiss

Note: This tool adds a non-functional digital signature block to the end 
of Python files to verify that the source code has not been tampered with.
"""

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog
    )

    # Add help strings for the main arguments
    parser.add_argument(
        "action", 
        choices=["sign", "verify"], 
        help="Action to perform: 'sign' adds a hash block, 'verify' checks it"
    )
    
    parser.add_argument(
        "file", 
        help="The target Python (.py) file to process"
    )

    parser.add_argument(
        "--author", 
        default="@hejhdiss (Muhammed Shafin p)", 
        help="Author name to include in signature (default: @hejhdiss)"
    )
    
    parser.add_argument(
        "--license", 
        default="GPL-3.0", 
        help="License type to include in signature (default: GPL-3.0)"
    )

    args = parser.parse_args()

    if args.action == "sign":
        sign_file(args.file, args.author, args.license)
    elif args.action == "verify":
        verify_file(args.file)

if __name__ == "__main__":
    main()
