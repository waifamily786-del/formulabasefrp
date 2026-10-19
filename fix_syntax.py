"""Fix all syntax errors in pdf_auto_filler.py - remove stray single quotes before ))"""
import re

path = r'backend\modules\pdf_invoice_engine\pdf_auto_filler.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The pattern is: .startswith(("<<", "{{"'))  ->  .startswith(("<<", "{{"))
# Also handles: .startswith(("<<", "{{"'))]  ->  .startswith(("<<", "{{"))]
fixed = re.sub(
    r'''\.startswith\(\("<<", "\{\{\"'\)\)''',
    '.startswith(("<<", "{{"))',
    content
)
fixed = re.sub(
    r'''\.startswith\(\("<<", "\{\{\"'\)\)\]''',
    '.startswith(("<<", "{{"))]',
    fixed
)

# Count replacements
orig_count = content.count('"{{\"\')')
print(f"Found {orig_count} occurrences of bad pattern")

with open(path, 'w', encoding='utf-8') as f:
    f.write(fixed)

# Verify
import ast
try:
    ast.parse(fixed)
    print("SUCCESS: No more syntax errors in pdf_auto_filler.py!")
except SyntaxError as e:
    print(f"Still has SyntaxError at line {e.lineno}: {e.msg}")
    print(f"  Text: {e.text}")
    # Find and show all bad lines
    lines = fixed.split('\n')
    for i, line in enumerate(lines):
        if "'))" in line and "startswith" in line:
            print(f"  Suspicious line {i+1}: {repr(line)}")
