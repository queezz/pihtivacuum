from cryptography.fernet import Fernet

# Generate and save a key (do this once and store the key securely)
def generate_key():
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file:
        key_file.write(key)
    print("Key generated and saved as 'secret.key'.")

# Load the encryption key
def load_key():
    return open("secret.key", "rb").read()

# Encrypt the file
def encrypt_file(input_file, output_file):
    key = load_key()
    fernet = Fernet(key)

    with open(input_file, "rb") as file:
        file_data = file.read()

    encrypted_data = fernet.encrypt(file_data)

    with open(output_file, "wb") as file:
        file.write(encrypted_data)
    print(f"File '{input_file}' encrypted as '{output_file}'.")

# Decrypt the file
def decrypt_file(input_file, output_file):
    key = load_key()
    fernet = Fernet(key)

    with open(input_file, "rb") as file:
        encrypted_data = file.read()

    decrypted_data = fernet.decrypt(encrypted_data)

    with open(output_file, "wb") as file:
        file.write(decrypted_data)
    print(f"File '{input_file}' decrypted as '{output_file}'.")

from cryptography.fernet import Fernet

def generate_key():
    """Generate and save a valid Fernet key"""
    key = Fernet.generate_key()  # This generates a 32-byte key
    with open("secret.key", "wb") as key_file:
        key_file.write(key)
    print("Key generated and saved as 'secret.key'.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python encrypt_users.py <generate_key|encrypt|decrypt> <input_file> [<output_file>]")
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
        output_file = sys.argv[3] if len(sys.argv) > 3 else input_file.replace(".enc", "")
        decrypt_file(input_file, output_file)
    else:
        print("Invalid command or insufficient arguments.")
        print("Usage: python encrypt_users.py <generate_key|encrypt|decrypt> <input_file> [<output_file>]")