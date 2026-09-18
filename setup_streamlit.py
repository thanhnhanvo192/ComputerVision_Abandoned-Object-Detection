import os

p = os.path.expanduser('~/.streamlit')
os.makedirs(p, exist_ok=True)
cred_path = os.path.join(p, 'credentials.toml')

with open(cred_path, 'w', encoding='utf-8') as f:
    f.write('[general]\nemail = ""\n')

print(f"[OK] Created Streamlit credentials file at: {cred_path}")
