"""Utility to add users with hashed passwords to users.json."""

import json
from werkzeug.security import generate_password_hash

USERS_FILE = "users.json"


def load_users():
    try:
        with open(USERS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_users(users):
    with open(USERS_FILE, "w") as file:
        json.dump(users, file, indent=4)


def add_user(username, password):
    users = load_users()
    if username in users:
        print(f"User '{username}' already exists. Overwriting password.")
    users[username] = generate_password_hash(password)
    save_users(users)
    print(f"User '{username}' added/updated successfully.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python -m pihti.hash_passwords <username> <password>")
    else:
        add_user(sys.argv[1], sys.argv[2])
