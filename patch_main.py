with open("context_creator/main.py", "r") as f:
    content = f.read()

content = content.replace("get_project_structure.cache_clear()", "# get_project_structure.cache_clear()")

with open("context_creator/main.py", "w") as f:
    f.write(content)
