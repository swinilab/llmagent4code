import ast
import sys

for fname in sys.argv[1:]:
    try:
        with open(fname) as f:
            ast.parse(f.read())
        print(f"{fname}: OK")
    except SyntaxError as e:
        print(f"{fname}: SyntaxError at line {e.lineno}: {e.msg}")
        sys.exit(1)
