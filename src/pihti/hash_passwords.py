"""Utility to add users with hashed passwords to users.json."""

import json
from getpass import getpass
from pathlib import Path

from werkzeug.security import generate_password_hash

USERS_FILE = "users.json"


def load_users():
    try:
        return json.loads(Path(USERS_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_users(users):
    Path(USERS_FILE).write_text(json.dumps(users, indent=4) + "\n", encoding="utf-8")


def add_user(username, password):
    users = load_users()
    if username in users:
        print(f"User '{username}' already exists. Overwriting password.")
    users[username] = generate_password_hash(password)
    save_users(users)
    print(f"User '{username}' added/updated successfully.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) not in {2, 3}:
        print("Usage: python -m pihti.hash_passwords <username> [password]")
    else:
        password = sys.argv[2] if len(sys.argv) == 3 else getpass("Password: ")
        add_user(sys.argv[1], password)
