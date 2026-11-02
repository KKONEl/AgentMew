import ast
import difflib
import hashlib

source = 'API_TOKEN = "demo-secret"\ndef calculate(text):\n    return eval(text)\n'
before = hashlib.sha256(source.encode()).hexdigest()

def audit(code):
    findings = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [(exc.lineno, 'syntax-error')]
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name) and any(x in target.id.lower() for x in ('secret', 'token', 'password')):
                    findings.append((node.lineno, 'possible-hardcoded-secret'))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('eval', 'exec'):
            findings.append((node.lineno, 'dynamic-execution'))
    return sorted(findings)

findings = audit(source)
assert findings == [(1, 'possible-hardcoded-secret'), (3, 'dynamic-execution')]
assert audit('message = "eval(text)"\n') == []
assert audit('def broken(:') == [(1, 'syntax-error')]
# A candidate only: it is never applied or executed.
suggestion = 'import ast\nimport os\nAPI_TOKEN = os.environ["API_TOKEN"]\ndef calculate(text):\n    return ast.literal_eval(text)\n'
patch = ''.join(difflib.unified_diff(source.splitlines(True), suggestion.splitlines(True), fromfile='a/app.py', tofile='b/app.py'))
assert 'literal_eval' in patch and 'os.environ' in patch
assert hashlib.sha256(source.encode()).hexdigest() == before
runs = [
    dict(outcome=True, trajectory=True, state=True, critical=0),
    dict(outcome=True, trajectory=False, state=True, critical=1),
    dict(outcome=False, trajectory=True, state=False, critical=0),
]
verified = sum(r['outcome'] and r['trajectory'] and r['state'] for r in runs)/len(runs)
raw_success = sum(r['outcome'] for r in runs)/len(runs)
critical = sum(r['critical'] for r in runs)
release = raw_success >= 0.60 and critical == 0 and verified >= 0.60
assert raw_success >= 0.60 and not release
print('findings:', findings)
print('candidate patch:')
print(patch, end='')
print(f'outcome={raw_success:.3f} verified={verified:.3f} critical={critical} release={release}')
print('original unchanged; reviewed code was never executed')
