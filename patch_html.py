with open("context_creator/templates/index.html", "r") as f:
    content = f.read()

old_selection = '<span id="selected-count" class="font-bold mr-1">0</span> files selected'
new_selection = '<span id="selected-count" class="font-bold mr-1">0</span> files selected <span class="text-xs ml-1 text-blue-600/70">(<span id="selected-tokens">0</span> tokens)</span>'

content = content.replace(old_selection, new_selection)

with open("context_creator/templates/index.html", "w") as f:
    f.write(content)
