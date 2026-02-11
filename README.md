# Interactive Vacuum
Interactive vacuum diagram for PIHTI

## SVG settings
Elements are named ins `diagram.svg` and element interactions are defined in `static/elementsConfig.json`

## Install and run

Install the project (from the project root):

```bash
pip install .
```

Start the server:

```bash
python server.py
```

(Or run `server.py` directly without installing: `python server.py`)

## Add user
```bash
python hash_passwords.py admin newpassword
```

```bash
python encrypt_users.py encrypt users.json users.json.enc
```

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