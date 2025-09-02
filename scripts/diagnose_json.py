import json

with open('data/MASTER.json', 'r', encoding='utf-8') as f:
    content = f.read()

print(f'File size: {len(content)} characters')

# Try to find the largest valid JSON prefix
max_valid = 0
for i in range(len(content)):
    try:
        json.loads(content[:i+1])
        max_valid = i+1
    except:
        pass

print(f'Valid JSON prefix ends at: {max_valid}')
print(f'Remaining invalid content: {len(content) - max_valid} characters')

if max_valid < len(content):
    invalid_part = content[max_valid:]
    print('Invalid content starts with:')
    print(repr(invalid_part[:100]))

# Show the structure around where it breaks
lines = content.splitlines()
char_count = 0
for line_num, line in enumerate(lines):
    if char_count <= max_valid <= char_count + len(line):
        print(f'Break occurs around line {line_num + 1}')
        start = max(0, line_num - 3)
        end = min(len(lines), line_num + 4)
        for i in range(start, end):
            marker = ' --> ' if i == line_num else '     '
            print(f'{marker}{i+1:4d}: {lines[i]}')
        break
    char_count += len(line) + 1  # +1 for newline
