import re

# Read UserController.py
with open('app/api/endpoints/UserController.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace X_Authorization parameters with commented versions
# Match patterns like: X_Authorization: str = Header(alias="X-Authorization"),
# Or: X_Authorization: Optional[str] = Header(default=None, alias="X-Authorization"),
pattern = r'(\s+)(X_Authorization: (?:str|Optional\[str\]) = Header\([^)]+\)),'
replacement = r'\1# \2,'

content = re.sub(pattern, replacement, content)

# Write back
with open('app/api/endpoints/UserController.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully commented out all X_Authorization parameters in UserController.py")
