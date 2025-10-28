from pathlib import Path

p = Path("prompts/base_prompt.txt")
print(p.resolve())   # see the absolute target
print(p.exists())    # does it actually exist?
