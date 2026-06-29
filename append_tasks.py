import re

with open("/tmp/sprint_their.yaml", "r") as f:
    their = f.read()

# Find the start of TASK-005
idx = their.find("  - key: TASK-005")
if idx != -1:
    tasks_to_add = their[idx:]
    with open("docs/sprint-status.yaml", "a") as f:
        f.write("\n" + tasks_to_add)
    print("Tasks appended.")
else:
    print("TASK-005 not found!")
