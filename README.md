# Interactive Vacuum
Interactive vacuum diagram for PIHTI

## SVG settings
Elements are named ins `diagram.svg` and element interactions are defined in `static/elementsConfig.json`

## Start server
Simply run `server.py`:
```
python server.py
```

## Add user
```bash
python hash_passwords.py admin newpassword
```

```bash
python encrypt_users.py encrypt users.json users.json.enc
```
