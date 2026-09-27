content = open('outputs/report.html', encoding='utf-8').read()

checks = {
    'Has doctype': content.startswith('<!doctype html>'),
    'Has closing body': '</body>' in content,
    'Has closing html': '</html>' in content,
    'Shows before fix 2309': 'before fix: 2309' in content,
    'Shows after fix 0': 'after fix: 0' in content,
    'Requested analysis label': 'Requested analysis' in content,
    'Additional finding label': 'Additional finding' in content,
    'AI disclosure present': 'Rs 0 paid model cost' in content,
    'Potential excess cost wording': 'Potential excess cost' in content,
    'Known gaps section': 'Known gaps' in content,
}

print('=== HTML Content Checks ===')
all_ok = True
for k, v in checks.items():
    status = 'OK' if v else 'FAIL'
    if not v:
        all_ok = False
    print(f'  [{status}] {k}')

print(f'HTML size: {len(content)} bytes')
result = 'PASS' if all_ok else 'FAIL'
print(f'All checks: {result}')
