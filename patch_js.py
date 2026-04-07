with open("context_creator/static/js/main.js", "r") as f:
    content = f.read()

# Update updateSelectionCounter function
old_updateSelectionCounter = """    updateSelectionCounter() {
        const count = this.selectedPaths.size;
        if (this.elements.selectedCount) this.elements.selectedCount.textContent = count;

        if (this.elements.selectionCounter) {
            if (count > 0) {
                this.elements.selectionCounter.classList.remove('hidden');
                this.elements.selectionCounter.classList.add('flex');
            } else {
                this.elements.selectionCounter.classList.add('hidden');
                this.elements.selectionCounter.classList.remove('flex');
            }
        }

        if (this.elements.processBtn) {
            this.elements.processBtn.disabled = count === 0;
        }
    }"""

new_updateSelectionCounter = """    updateSelectionCounter() {
        const count = this.selectedPaths.size;
        let totalTokens = 0;

        // Calculate total tokens
        this.selectedPaths.forEach(path => {
            const node = this.findNodeByPath(this.projectStructure, path);
            if (node && node.type === 'file' && node.tokens) {
                totalTokens += node.tokens;
            }
        });

        if (this.elements.selectedCount) this.elements.selectedCount.textContent = count;

        const selectedTokensElement = document.getElementById('selected-tokens');
        if (selectedTokensElement) {
            selectedTokensElement.textContent = this.formatTokens(totalTokens);
        }

        if (this.elements.selectionCounter) {
            if (count > 0) {
                this.elements.selectionCounter.classList.remove('hidden');
                this.elements.selectionCounter.classList.add('flex');
            } else {
                this.elements.selectionCounter.classList.add('hidden');
                this.elements.selectionCounter.classList.remove('flex');
            }
        }

        if (this.elements.processBtn) {
            this.elements.processBtn.disabled = count === 0;
        }
    }

    formatTokens(tokens) {
        if (!tokens) return '0';
        if (tokens >= 1000000) {
            return (tokens / 1000000).toFixed(1) + 'M';
        }
        if (tokens >= 1000) {
            return (tokens / 1000).toFixed(1) + 'k';
        }
        return tokens.toString();
    }"""

content = content.replace(old_updateSelectionCounter, new_updateSelectionCounter)

# Update renderNodes function to show token count
old_nameSpan = """            // Name
            const nameSpan = document.createElement('span');
            nameSpan.className = `text-gray-700 text-[13px] leading-6 ${node.type === 'file' ? 'file-name' : 'font-medium'}`;
            if (this.filterText && node.type === 'file' && !this.isRegexMode) {
                this.highlightMatch(nameSpan, node.name, this.filterText);
            } else {
                nameSpan.textContent = node.name;
            }
            div.appendChild(nameSpan);"""

new_nameSpan = """            // Name
            const nameSpan = document.createElement('span');
            nameSpan.className = `text-gray-700 text-[13px] leading-6 flex-1 ${node.type === 'file' ? 'file-name' : 'font-medium'}`;
            if (this.filterText && node.type === 'file' && !this.isRegexMode) {
                this.highlightMatch(nameSpan, node.name, this.filterText);
            } else {
                nameSpan.textContent = node.name;
            }
            div.appendChild(nameSpan);

            // Token count for files
            if (node.type === 'file') {
                const tokenSpan = document.createElement('span');
                tokenSpan.className = 'text-xs text-gray-400 ml-2';
                const tokens = node.tokens || 0;
                tokenSpan.textContent = `~${this.formatTokens(tokens)} tokens`;
                div.appendChild(tokenSpan);
            }"""

content = content.replace(old_nameSpan, new_nameSpan)

with open("context_creator/static/js/main.js", "w") as f:
    f.write(content)
