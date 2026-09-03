"""Utility to generate Fernet keys and encrypt/decrypt user files."""

import os
from pathlib import Path

from cryptography.fernet import Fernet


def key_path() -> Path:
    if configured := os.environ.get("PIHTI_USERS_KEY_FILE"):
        return Path(configured).expanduser()
    if local_app_data := os.environ.get("LOCALAPPDATA"):
        return Path(local_app_data) / "pihti-diagram" / "users.key"
    return Path.home() / ".config" / "pihti-diagram" / "users.key"


def generate_key(force=False):
    """Generate and save a valid Fernet key."""
    destination = key_path()
    if destination.exists() and not force:
        raise FileExistsError("A users key already exists; refusing to overwrite it.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(Fernet.generate_key())
    destination.chmod(0o600)
    print("Users key generated in private application storage.")


def load_key():
    return key_path().read_bytes().strip()


def encrypt_file(input_file, output_file):
    key = load_key()
    fernet = Fernet(key)
    file_data = Path(input_file).read_bytes()
    encrypted_data = fernet.encrypt(file_data)
    Path(output_file).write_bytes(encrypted_data)
    print(f"File '{input_file}' encrypted as '{output_file}'.")


def decrypt_file(input_file, output_file):
    key = load_key()
    fernet = Fernet(key)
    encrypted_data = Path(input_file).read_bytes()
    decrypted_data = fernet.decrypt(encrypted_data)
    Path(output_file).write_bytes(decrypted_data)
    print(f"File '{input_file}' decrypted as '{output_file}'.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python -m pihti.encrypt_users <generate_key|encrypt|decrypt> <input_file> [<output_file>]"
        )
        sys.exit(1)

    command = sys.argv[1]
    if command == "generate_key":
        generate_key()
    elif command == "encrypt" and len(sys.argv) >= 3:
        input_file = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else f"{input_file}.enc"
        encrypt_file(input_file, output_file)
    elif command == "decrypt" and len(sys.argv) >= 3:
        input_file = sys.argv[2]
        output_file = (
            sys.argv[3] if len(sys.argv) > 3 else input_file.replace(".enc", "")
        )
        decrypt_file(input_file, output_file)
    else:
        print("Invalid command or insufficient arguments.")
        print(
            "Usage: python -m pihti.encrypt_users <generate_key|encrypt|decrypt> <input_file> [<output_file>]"
        )
