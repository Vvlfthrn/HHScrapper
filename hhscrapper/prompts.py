try:
    with open('../resume.txt', 'r') as f:
        RESUME = f.read()
except FileNotFoundError:
    with open('../resume.sample.txt', 'w') as f:
        RESUME = f.read()

try:
    with open('../prompt.txt', 'r') as f:
        PROMPT = f.read()
except FileNotFoundError:
    with open('../prompt.sample.txt', 'w') as f:
        PROMPT = f.read()

