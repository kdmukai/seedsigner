"""
Finds the "POT-Creation-Date" line in messages.pot and deletes it.
"""
import os
import subprocess


# Store the current version of the POT file
messages_path = os.path.join(os.getcwd(), "babel", "messages.pot")
lines = []
with open(messages_path, 'r') as f:
    lines = f.readlines()

print("Read the original POT file")

# Regenerate the POT file
subprocess.check_output(["python", "setup.py", "extract_messages"])

print("Regenerated the POT file")

# Remove the "POT-Creation-Date" line from the new POT file
regenerated_lines = []
with open(messages_path, 'r') as f:
    regenerated_lines = f.readlines()
    for i, line in enumerate(regenerated_lines):
        if line.startswith("\"POT-Creation-Date"):
            del regenerated_lines[i]
            print("Removed the POT-Creation-Date line")
            break

# Write the changes back into the POT file
with open(messages_path, 'w') as f:
    f.writelines(regenerated_lines)

print("Wrote the changes back into the POT file")

# Compare; "fail" commit if there are changes in order to notify the user
for orig_line, new_line in zip(lines, regenerated_lines):
    if orig_line != new_line:
        print(orig_line)
        print(new_line)
        print("babel/messages.pot has been regenerated with changes. Current commit aborted.")
        print("Re-run your commit; ensure that you include the updated babel/messages.pot.")
        exit(1)

print("No changes detected in babel/messages.pot; continuing commit.")