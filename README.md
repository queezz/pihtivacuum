# Interactive Vacuum
Interactive vacuum diagram for PIHTI

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

## Add user
```bash
python -m pihti.hash_passwords admin newpassword
```

```bash
python -m pihti.encrypt_users encrypt users.json users.json.enc
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