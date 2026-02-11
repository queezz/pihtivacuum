# Interactive Vacuum
Interactive vacuum diagram for PIHTI

## Contents

- [SVG settings](#svg-settings)
- [Install and run](#install-and-run)
- [User Management (Lightweight Access Control)](#-user-management-lightweight-access-control)
  - [Files involved](#-files-involved)
  - [First-Time Setup (New Machine)](#-first-time-setup-new-machine)
  - [Add or Update a User](#-add-or-update-a-user)
  - [Encrypt Users File](#-encrypt-users-file-before-syncing-to-github)
  - [Decrypt Users File](#-decrypt-users-file-after-pulling-from-github)
  - [Typical Workflow](#-typical-workflow)
  - [Notes](#-notes)
  - [Quick CLI (manage_users)](#-quick-cli-manage_users)
- [venv](#venv)

---

## SVG settings
Elements are named in `diagram.svg` and element interactions are defined in `static/elementsConfig.json`

## Install and run

Install the project (from the project root):

```bash
pip install .
```

Or editable install for development:

```bash
pip install -e .
```

Start the server:

```bash
python -m pihti
```

---

# 👤 User Management (Lightweight Access Control)

This project uses a simple user system:

* Passwords are **hashed**
* User file can be **encrypted**
* Encryption key is **kept locally and copied manually**
* This is **not high security**, just to avoid exposing names/IDs publicly

---

## 📁 Files involved

| File             | Purpose                                |
| ---------------- | -------------------------------------- |
| `users.json`     | Plain user database (hashed passwords) |
| `users.json.enc` | Encrypted version (safe to sync)       |
| `secret.key`     | Local encryption key (DO NOT COMMIT)   |

---

## 🔐 First-Time Setup (New Machine)

### 1️⃣ Generate encryption key

```bash
python -m pihti.encrypt_users generate_key
```

This creates:

```
secret.key
```

⚠️ **Never commit this file.**
Copy it manually to any machine that needs access.

---

## 👤 Add or Update a User

This hashes the password automatically.

```bash
python -m pihti.hash_passwords <username> <password>
```

Example:

```bash
python -m pihti.hash_passwords arseny mypassword123
```

This updates:

```
users.json
```

Passwords are stored hashed using Werkzeug.

⚠️ **Important:** The server reads from `users.json.enc`. After adding a user, run `encrypt` so the server can authenticate the new user. No server restart needed.

---

## 🔒 Encrypt Users File (Before Syncing to GitHub)

```bash
python -m pihti.encrypt_users encrypt users.json users.json.enc
```

Now you can safely:

* Commit `users.json.enc`
* Do NOT commit `users.json`
* Do NOT commit `secret.key`

Optional: delete plaintext file after encryption:

```bash
rm users.json
```

(PowerShell: `Remove-Item users.json`)

---

## 🔓 Decrypt Users File (After Pulling from GitHub)

Make sure `secret.key` exists locally.

```bash
python -m pihti.encrypt_users decrypt users.json.enc users.json
```

You can now:

* Add users
* Modify users
* Re-encrypt afterwards

---

## 🔁 Typical Workflow

### On your main machine

```
decrypt
add user
encrypt
commit .enc
```

### On another machine

```
pull
copy secret.key manually
decrypt
```

---

## 🧠 Notes

* This system is designed for **convenience**, not strong security.
* Anyone with `secret.key` can decrypt users.
* Passwords are hashed — they are never stored in plaintext.
* If `secret.key` is lost, encrypted files cannot be recovered.

---

## 🛠️ Quick CLI (manage_users)

One-command wrapper for common tasks:

```bash
python -m pihti.manage_users generate_key       # Create secret.key
python -m pihti.manage_users add <user> <pw>   # Add/update user
python -m pihti.manage_users encrypt           # users.json -> users.json.enc
python -m pihti.manage_users decrypt           # users.json.enc -> users.json
```

Or use the underlying modules directly:

```bash
python -m pihti.hash_passwords <username> <password>
python -m pihti.encrypt_users generate_key
python -m pihti.encrypt_users encrypt users.json users.json.enc
python -m pihti.encrypt_users decrypt users.json.enc users.json
```

---

# venv

Create
```
python -m venv "$HOME/.venvs/pihti"
```
activate
```
& $env:USERPROFILE\.venvs\pihti\Scripts\Activate.ps1
```

delete, only if you need to re-install venv:
```powershell
Remove-Item -Recurse -Force $env:USERPROFILE\.venvs\pihti
```