"""One-command CLI wrapper for user management."""

import sys

USERS_JSON = "users.json"
USERS_ENC = "users.json.enc"


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python -m pihti.manage_users <generate_key|add|hash_passwords|encrypt|decrypt> [args...]"
        )
        print("  generate_key         Create secret.key")
        print("  add <user> <pw>      Add/update user (hashes password)")
        print("  hash_passwords <user> <pw>  Same as add")
        print("  encrypt              users.json -> users.json.enc")
        print("  decrypt              users.json.enc -> users.json")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "generate_key":
        from pihti.encrypt_users import generate_key
        generate_key()

    elif cmd in ("add", "hash_passwords"):
        if len(sys.argv) != 4:
            print("Usage: python -m pihti.manage_users add <username> <password>")
            sys.exit(1)
        from pihti.hash_passwords import add_user
        add_user(sys.argv[2], sys.argv[3])

    elif cmd == "encrypt":
        from pihti.encrypt_users import encrypt_file
        encrypt_file(USERS_JSON, USERS_ENC)

    elif cmd == "decrypt":
        from pihti.encrypt_users import decrypt_file
        decrypt_file(USERS_ENC, USERS_JSON)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
