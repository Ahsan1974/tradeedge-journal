#!/usr/bin/env python3
"""Generate a bcrypt password hash for ADMIN_PASSWORD_HASH."""

from __future__ import annotations

import getpass
import sys

import bcrypt


def main() -> int:
    print("TradeEdge Journal — password hash generator")
    print("The password is never stored; only the bcrypt hash is printed.\n")
    password = getpass.getpass("Enter password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    if len(password) < 8:
        print("Warning: password is shorter than 8 characters.", file=sys.stderr)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    print("\nAdd this to your .env file:\n")
    print(f"ADMIN_PASSWORD_HASH={hashed.decode('utf-8')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
