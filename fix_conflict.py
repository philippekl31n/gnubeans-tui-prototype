import re
with open("docs/sprint-status.yaml", "r") as f:
    content = f.read()

# HEAD is EPIC-002-gemini (with the modified TASK-004 ACs)
# The conflict is:
# <<<<<<< HEAD
# (TASK-004 modified ACs)
# =======
# (TASK-008 ACs)
# >>>>>>> a137bd2 (docs: add epic-3 tasks to sprint-status.yaml)

# Actually, let's just do it manually. We can extract the HEAD part and the their part.
def resolve(match):
    head_content = match.group(1)
    their_content = match.group(2)
    # HEAD has the modified TASK-004 ACs.
    # Theirs has the rest of TASK-008. But wait, did Theirs also contain the old TASK-004 ACs?
    # Let's just print it to understand exactly what's inside.
    return head_content + their_content

new_content, count = re.subn(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [^\n]+\n', resolve, content, flags=re.DOTALL)
with open("docs/sprint-status.yaml", "w") as f:
    f.write(new_content)
print(f"Replaced {count} conflicts")
