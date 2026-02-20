# Interactive Vacuum
Interactive vacuum diagram for PIHTI

## Contents

- [Interactive Vacuum](#interactive-vacuum)
  - [Contents](#contents)
  - [SVG settings](#svg-settings)
- [🐍 Virtual Environment (Required)](#-virtual-environment-required)
  - [🚀 Running the Server](#-running-the-server)
  - [ 🍓 Raspberry Pi service deployment](#--raspberry-pi-service-deployment)
  - [🔄 Updating the running service](#-updating-the-running-service)
- [👤 User Management (Lightweight Access Control)](#-user-management-lightweight-access-control)
  - [📁 Files involved](#-files-involved)
  - [🔐 First-Time Setup (New Machine)](#-first-time-setup-new-machine)
    - [1️⃣ Generate encryption key](#1️⃣-generate-encryption-key)
  - [👤 Add or Update a User](#-add-or-update-a-user)
  - [🔒 Encrypt Users File (Before Syncing to GitHub)](#-encrypt-users-file-before-syncing-to-github)
  - [🔓 Decrypt Users File (After Pulling from GitHub)](#-decrypt-users-file-after-pulling-from-github)
  - [🔁 Typical Workflow](#-typical-workflow)
    - [On your main machine](#on-your-main-machine)
    - [On another machine](#on-another-machine)
  - [🧠 Notes](#-notes)
  - [🛠️ Quick CLI (manage\_users)](#️-quick-cli-manage_users)

---

## <a id="svg-settings"></a>SVG settings
Elements are named in `diagram.svg` and element interactions are defined in `static/elementsConfig.json`

---

# <a id="venv"></a>🐍 Virtual Environment (Required)

We install PIHTI into a dedicated virtual environment.

We use a virtual environment to isolate dependencies and avoid breaking system Python. This keeps your OS clean and prevents version conflicts.

**Create venv**

Linux / macOS / Raspberry Pi:

```bash
python3 -m venv ~/.venvs/pihti
```

Windows PowerShell:

```powershell
python -m venv "$HOME/.venvs/pihti"
```

**Activate venv**

Linux / macOS / Raspberry Pi:

```bash
source ~/.venvs/pihti/bin/activate
```

Windows PowerShell:

```powershell
& $env:USERPROFILE\.venvs\pihti\Scripts\Activate.ps1
```

After activation you should see `(pihti)` in your terminal prompt.

**Install PIHTI** (inside activated venv)

From the project root:

```bash
pip install .
```

For development:

```bash
pip install -e .
```

**Quick Run** (after activation, from project root):

```bash
python -m pihti run
```

**Remove venv** (only if needed)

Linux/macOS:

```bash
rm -rf ~/.venvs/pihti
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force $env:USERPROFILE\.venvs\pihti
```

---

## <a id="running-the-server"></a>🚀 Running the Server

Run from the **project root** (where `pyproject.toml` lives). The server reads `settings.json`, `logs.csv`, etc. from the current directory.

```bash
python -m pihti run
```

**Background mode (Linux / Raspberry Pi):**

```bash
python -m pihti run --nohup
```

Output appends to `pihti.log`. The process survives terminal close.

Optional host/port:

```bash
python -m pihti run --host 0.0.0.0 --port 5000
python -m pihti run --nohup --port 8000
```

---
## <a id="raspberry-pi-service-deployment"></a> 🍓 Raspberry Pi service deployment

**Copy service file**
`pihti.service` needs to know 

1. where the repo is on the RasPi
2. which venv to use
Currently, that is as below:

```
WorkingDirectory=/home/pi/pihtivacuum
ExecStart=/home/pi/.venvs/pihti/bin/python -m pihti run
```
Now let's start the service.

The server repo lives in `/home/pi/pihtivacuum`:
```bash
cd /home/pi/pihtivacuum
sudo cp deploy/pihti.service /etc/systemd/system/pihti.service
```

**Enable and start service**

```bash
sudo systemctl daemon-reload
sudo systemctl enable pihti
sudo systemctl start pihti
```

**Check status and logs**

```bash
systemctl status pihti
journalctl -u pihti -f
```

**Stop / restart service**

```bash
sudo systemctl stop pihti
sudo systemctl restart pihti
```

**(Optional) nginx reverse proxy**

```bash
cd /path/to/pihti-repo
sudo apt install nginx
sudo cp deploy/nginx-pihti.conf /etc/nginx/sites-available/pihti
sudo ln -s /etc/nginx/sites-available/pihti /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔄 Updating the running service

After pulling new changes from Git, what you need to do depends on what changed.

**1️⃣ Python source code, templates, static files**

```bash
git pull
sudo systemctl restart pihti
```

**2️⃣ Python dependencies changed (pyproject.toml)**

```bash
git pull
source ~/.venvs/pihti/bin/activate
pip install -e .
sudo systemctl restart pihti
```

**3️⃣ Service file changed (deploy/pihti.service)**

```bash
git pull
sudo cp deploy/pihti.service /etc/systemd/system/pihti.service
sudo systemctl daemon-reload
sudo systemctl restart pihti
```

**4️⃣ nginx config changed (deploy/nginx-pihti.conf)**

```bash
git pull
sudo cp deploy/nginx-pihti.conf /etc/nginx/sites-available/pihti
sudo nginx -t
sudo systemctl reload nginx
```

---

# <a id="user-management-lightweight-access-control"></a>👤 User Management (Lightweight Access Control)

This project uses a simple user system:

* Passwords are **hashed**
* User file can be **encrypted**
* Encryption key is **kept locally and copied manually**
* This is **not high security**, just to avoid exposing names/IDs publicly

---

## <a id="files-involved"></a>📁 Files involved

| File             | Purpose                                |
| ---------------- | -------------------------------------- |
| `users.json`     | Plain user database (hashed passwords) |
| `users.json.enc` | Encrypted version (safe to sync)       |
| `secret.key`     | Local encryption key (DO NOT COMMIT)   |

---

## <a id="first-time-setup-new-machine"></a>🔐 First-Time Setup (New Machine)

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

## <a id="add-or-update-a-user"></a>👤 Add or Update a User

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

## <a id="encrypt-users-file-before-syncing-to-github"></a>🔒 Encrypt Users File (Before Syncing to GitHub)

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

## <a id="decrypt-users-file-after-pulling-from-github"></a>🔓 Decrypt Users File (After Pulling from GitHub)

Make sure `secret.key` exists locally.

```bash
python -m pihti.encrypt_users decrypt users.json.enc users.json
```

You can now:

* Add users
* Modify users
* Re-encrypt afterwards

---

## <a id="typical-workflow"></a>🔁 Typical Workflow

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

## <a id="notes"></a>🧠 Notes

* This system is designed for **convenience**, not strong security.
* Anyone with `secret.key` can decrypt users.
* Passwords are hashed — they are never stored in plaintext.
* If `secret.key` is lost, encrypted files cannot be recovered.

---

## <a id="quick-cli-manage_users"></a>🛠️ Quick CLI (manage_users)

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
