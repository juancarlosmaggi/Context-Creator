document.addEventListener('DOMContentLoaded', () => {
    new ProjectExplorer();
});

class ProjectExplorer {
    constructor() {
        this.projectStructure = null;
        this.filteredStructure = null;
        this.selectedPaths = new Set();
        this.filterText = '';
        this.projectName = '';
        this.isRegexMode = false;

        this.elements = {
            projectStructure: document.getElementById('project-structure'),
            fileFilter: document.getElementById('file-filter'),
            regexModeCheckbox: document.getElementById('regex-mode'),
            clearFilterBtn: document.getElementById('clear-filter'),
            expandAllBtn: document.getElementById('expand-all'),
            collapseAllBtn: document.getElementById('collapse-all'),
            selectAllBtn: document.getElementById('select-all'),
            deselectAllBtn: document.getElementById('deselect-all'),
            refreshIndexBtn: document.getElementById('refresh-index'),
            processForm: document.getElementById('process-form'),
            processBtn: document.getElementById('process-button'),
            selectedCount: document.getElementById('selected-count'),
            selectionCounter: document.getElementById('selection-counter'),
            toastContainer: document.getElementById('toast-container'),
            projectHeading: document.getElementById('project-heading')
        };

        this.init();
    }

    init() {
        this.bindEvents();
        this.fetchStructure();
    }

    bindEvents() {
        // Event delegation for checkbox changes
        this.elements.projectStructure.addEventListener('change', (event) => {
            if (event.target.type === 'checkbox') {
                this.handleCheckboxChange(event.target);
            }
        });

        // Filter events
        this.elements.fileFilter.addEventListener('input', () => {
            this.filterText = this.elements.fileFilter.value.trim();
            this.applyFilter();
        });

        this.elements.regexModeCheckbox.addEventListener('change', () => {
            this.isRegexMode = this.elements.regexModeCheckbox.checked;
            this.applyFilter();
        });

        this.elements.clearFilterBtn.addEventListener('click', () => {
            this.elements.fileFilter.value = '';
            this.filterText = '';
            this.applyFilter();
        });

        // Toolbar events
        this.elements.expandAllBtn.addEventListener('click', () => this.expandAll());
        this.elements.collapseAllBtn.addEventListener('click', () => this.collapseAll());
        this.elements.selectAllBtn.addEventListener('click', () => this.selectAll());
        this.elements.deselectAllBtn.addEventListener('click', () => this.deselectAll());
        this.elements.refreshIndexBtn.addEventListener('click', () => this.refreshIndex());

        // Process form
        this.elements.processForm.addEventListener('submit', (e) => this.handleProcess(e));
    }

    fetchStructure() {
        fetch('/api/project-structure')
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch structure');
                return response.json();
            })
            .then(data => {
                this.projectStructure = data;
                if (this.projectStructure && this.projectStructure.name) {
                    this.projectName = this.capitalizeFirstLetter(this.projectStructure.name);
                    document.title = `Project Explorer - ${this.projectName}`;
                    if (this.elements.projectHeading) {
                        this.elements.projectHeading.textContent = `Project Explorer - ${this.projectName}`;
                    }
                }
                this.projectStructure = this.removeEmptyDirectories(this.projectStructure);
                this.filteredStructure = this.projectStructure;
                this.render();
                this.loadSelections();
            })
            .catch(error => {
                console.error('Error:', error);
                this.elements.projectStructure.innerHTML = '<li class="text-red-500">Error loading project structure</li>';
            });
    }

    render(isFiltered = false) {
        const container = this.elements.projectStructure;
        container.innerHTML = '';

        // Remove existing filter info if any
        const existingInfo = document.getElementById('filter-info');
        if (existingInfo) existingInfo.remove();

        if (!this.filteredStructure || !this.filteredStructure.children || this.filteredStructure.children.length === 0) {
             if (this.filterText) {
                const info = document.createElement('div');
                info.id = 'filter-info';
                info.className = 'text-gray-500 mt-4 text-center';
                info.textContent = 'No files match the filter';
                container.appendChild(info);
             }
             return;
        }

        this.renderNodes(this.filteredStructure.children, container, isFiltered);
        this.updateCheckboxStates();
    }

    renderNodes(nodes, container, isFiltered) {
        if (!nodes || nodes.length === 0) return;

        // Sort directories first, then files
        nodes.sort((a, b) => {
            if (a.type !== b.type) {
                return a.type === 'directory' ? -1 : 1;
            }
            return a.name.localeCompare(b.name);
        });

        nodes.forEach(node => {
            if (node.type === 'directory' && (!node.children || node.children.length === 0)) {
                return;
            }

            const li = document.createElement('li');
            li.className = 'select-none'; // Prevent text selection while clicking

            const div = document.createElement('div');
            div.className = `flex items-center hover:bg-[#007AFF]/10 rounded-lg px-2 py-1.5 transition-colors group cursor-pointer ${node.type === 'file' ? 'file-item' : 'dir-item'}`;

            // Checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = node.path;
            checkbox.className = 'mr-3 h-4 w-4 text-blue-500 focus:ring-blue-500 border-gray-300 rounded cursor-pointer';
            // Stop propagation on checkbox click to prevent triggering row click
            checkbox.addEventListener('click', (e) => e.stopPropagation());

            div.appendChild(checkbox);

            // Toggle Icon / Spacer
            if (node.type === 'directory') {
                const toggleButton = document.createElement('div'); // Changed to div to avoid button nesting issues if any
                toggleButton.className = 'toggle mr-2 text-gray-400 hover:text-gray-600 cursor-pointer transform transition-transform duration-200';
                if (isFiltered) toggleButton.classList.add('rotate-90');
                toggleButton.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                `;
                div.appendChild(toggleButton);

                // Folder Icon
                div.innerHTML += `
                    <span class="mr-2 text-blue-500">
                        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                        </svg>
                    </span>
                `;
            } else {
                // Spacer for file indentation matching folder icon + toggle
                div.innerHTML += `
                    <span class="w-6 mr-2"></span>
                    <span class="mr-2 text-gray-400">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </span>
                `;
            }

            // Name
            const nameSpan = document.createElement('span');
            nameSpan.className = `text-gray-700 text-[13px] leading-6 ${node.type === 'file' ? 'file-name' : 'font-medium'}`;
            if (this.filterText && node.type === 'file' && !this.isRegexMode) {
                this.highlightMatch(nameSpan, node.name, this.filterText);
            } else {
                nameSpan.textContent = node.name;
            }
            div.appendChild(nameSpan);

            // Filter Action for Directory
            if (node.type === 'directory') {
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'ml-auto opacity-0 group-hover:opacity-100 transition-opacity';
                const filterBtn = document.createElement('button');
                filterBtn.type = 'button';
                filterBtn.className = 'p-1 text-gray-400 hover:text-blue-500 rounded';
                filterBtn.title = 'Filter to this folder';
                filterBtn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>';
                filterBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.filterToDirectory(node.path);
                });
                actionsDiv.appendChild(filterBtn);
                div.appendChild(actionsDiv);
            }

            li.appendChild(div);

            // Children Container
            if (node.type === 'directory') {
                const childUl = document.createElement('ul');
                childUl.className = `pl-6 space-y-0.5 border-l border-gray-200 ml-2.5 ${isFiltered ? '' : 'hidden'}`;
                li.appendChild(childUl);

                if (isFiltered && node.children && node.children.length > 0) {
                    this.renderNodes(node.children, childUl, isFiltered);
                }

                // Toggle logic
                const toggleHandler = (e) => {
                    // Don't toggle if clicking checkbox or action button (handled separately)
                    if (e.target.type === 'checkbox' || e.target.closest('button')) return;

                    if (childUl.classList.contains('hidden')) {
                        if (!childUl.hasChildNodes() && node.children) {
                            this.renderNodes(node.children, childUl);
                            this.updateCheckboxStates();
                        }
                        childUl.classList.remove('hidden');
                        div.querySelector('.toggle').classList.add('rotate-90');
                    } else {
                        childUl.classList.add('hidden');
                        div.querySelector('.toggle').classList.remove('rotate-90');
                    }
                };

                div.addEventListener('click', toggleHandler);
            } else {
                // Clicking file row toggles checkbox
                div.addEventListener('click', () => {
                   checkbox.checked = !checkbox.checked;
                   this.handleCheckboxChange(checkbox);
                });
            }

            container.appendChild(li);
        });
    }

    applyFilter() {
        if (!this.projectStructure) return;

        if (this.filterText === '') {
            this.filteredStructure = this.projectStructure;
            this.render(false);
        } else {
            this.filteredStructure = this.createFilteredStructure(this.projectStructure, this.filterText);
            this.render(true);
        }
    }

    createFilteredStructure(node, filterText) {
        const result = { ...node };
        if (node.type === 'file') {
            let matches = false;
            if (this.isRegexMode) {
                try {
                    const regex = new RegExp(filterText, 'i');
                    matches = regex.test(node.path);
                } catch (e) {
                    matches = false;
                }
            } else {
                matches = node.name.toLowerCase().includes(filterText.toLowerCase());
            }
            return matches ? result : null;
        }

        if (node.type === 'directory' && node.children) {
            result.children = node.children
                .map(child => this.createFilteredStructure(child, filterText))
                .filter(child => child !== null);
            return result.children.length > 0 ? result : null;
        }
        return result;
    }

    removeEmptyDirectories(node) {
        if (node.type !== 'directory') return node;
        if (!node.parent && node.children) { // Root
             node.children = node.children.map(c => this.removeEmptyDirectories(c)).filter(c => c !== null);
             return node;
        }
        if (node.children && node.children.length > 0) {
             node.children = node.children.map(c => this.removeEmptyDirectories(c)).filter(c => c !== null);
             if (node.children.length === 0) return null;
        } else {
            return null;
        }
        return node;
    }

    handleCheckboxChange(checkbox) {
        const path = checkbox.value;
        const currentStructure = this.filterText ? this.filteredStructure : this.projectStructure;
        const node = this.findNodeByPath(currentStructure, path);
        if (!node) return;

        if (checkbox.checked) {
            if (node.type === 'directory') this.selectDescendantFiles(node);
            else this.selectedPaths.add(path);
        } else {
            if (node.type === 'directory') this.deselectDescendantFiles(node);
            else this.selectedPaths.delete(path);
        }

        this.updateCheckboxStates();
        this.updateSelectionCounter();
        this.saveSelections();
    }

    updateCheckboxStates() {
        const currentStructure = this.filterText ? this.filteredStructure : this.projectStructure;
        const checkboxes = this.elements.projectStructure.querySelectorAll('input[type="checkbox"]');

        checkboxes.forEach(cb => {
            const path = cb.value;
            const node = this.findNodeByPath(currentStructure, path);
            if (!node) return;

            if (node.type === 'directory') {
                const allSelected = this.isAllDescendantsSelected(node);
                const someSelected = this.isSomeDescendantsSelected(node);
                cb.indeterminate = someSelected && !allSelected;
                cb.checked = allSelected;
            } else {
                cb.checked = this.selectedPaths.has(path);
                cb.indeterminate = false;
            }
        });
    }

    findNodeByPath(root, path) {
        if (root.path === path) return root;
        for (const child of root.children || []) {
            const found = this.findNodeByPath(child, path);
            if (found) return found;
        }
        return null;
    }

    getAllDescendantFiles(node) {
        let files = [];
        if (node.type === 'file') files.push(node);
        else if (node.children) {
            node.children.forEach(child => {
                files = files.concat(this.getAllDescendantFiles(child));
            });
        }
        return files;
    }

    selectDescendantFiles(node) {
        this.getAllDescendantFiles(node).forEach(file => this.selectedPaths.add(file.path));
    }

    deselectDescendantFiles(node) {
        this.getAllDescendantFiles(node).forEach(file => this.selectedPaths.delete(file.path));
    }

    isAllDescendantsSelected(node) {
        const descendantFiles = this.getAllDescendantFiles(node);
        if (descendantFiles.length === 0) return false;
        return descendantFiles.every(file => this.selectedPaths.has(file.path));
    }

    isSomeDescendantsSelected(node) {
        const descendantFiles = this.getAllDescendantFiles(node);
        return descendantFiles.some(file => this.selectedPaths.has(file.path));
    }

    updateSelectionCounter() {
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

        // Update process button state
        if (count > 0) {
            this.elements.processBtn.removeAttribute('disabled');
            this.elements.processBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            this.elements.processBtn.setAttribute('disabled', 'true');
            this.elements.processBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }

    handleProcess(event) {
        event.preventDefault();
        const formData = new FormData();
        this.selectedPaths.forEach(path => formData.append('selected_paths', path));

        // Show processing state
        const originalBtnText = this.elements.processBtn.innerHTML;
        this.elements.processBtn.innerHTML = `
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
        `;
        this.elements.processBtn.disabled = true;

        fetch('/process/', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.text();
        })
        .then(text => {
            navigator.clipboard.writeText(text).then(() => {
                this.showToast("Copied to clipboard!", "success");
            }).catch(err => {
                console.error('Failed to copy: ', err);
                this.showToast("Processed, but failed to copy to clipboard", "error");
            });
        })
        .catch(error => {
            console.error('Error:', error);
            this.showToast('Failed to process files', 'error');
        })
        .finally(() => {
            this.elements.processBtn.innerHTML = originalBtnText;
            this.elements.processBtn.disabled = false;
        });
    }

    expandAll() {
        // Find all closed toggles
        const closedToggles = Array.from(this.elements.projectStructure.querySelectorAll('.toggle:not(.rotate-90)'));
        closedToggles.forEach(t => {
            // Check if we need to render children (lazy loading)
            const parentLi = t.closest('li');
            const childUl = parentLi.querySelector('ul');

            if (childUl && !childUl.hasChildNodes()) {
                // Trigger the click event on the parent div to load children via the existing event handler
                const parentDiv = t.closest('div');
                parentDiv.click();
            } else if (childUl) {
                // Just toggle visibility if children are already rendered
                childUl.classList.remove('hidden');
                t.classList.add('rotate-90');
            }
        });
    }

    collapseAll() {
        const openToggles = this.elements.projectStructure.querySelectorAll('.toggle.rotate-90');
        openToggles.forEach(t => {
             const parentLi = t.closest('li');
             const ul = parentLi.querySelector('ul');
             if (ul) {
                 ul.classList.add('hidden');
                 t.classList.remove('rotate-90');
             }
        });
    }

    selectAll() {
        const currentStructure = this.filterText ? this.filteredStructure : this.projectStructure;
        this.selectDescendantFiles(currentStructure);
        this.updateCheckboxStates();
        this.updateSelectionCounter();
        this.saveSelections();
    }

    deselectAll() {
        const currentStructure = this.filterText ? this.filteredStructure : this.projectStructure;
        this.deselectDescendantFiles(currentStructure);
        this.updateCheckboxStates();
        this.updateSelectionCounter();
        this.saveSelections();
    }

    refreshIndex() {
        fetch('/api/rebuild-index', { method: 'POST' })
            .then(response => {
                if (!response.ok) throw new Error('Failed to rebuild index');
                return response.json();
            })
            .then(data => {
                if (data.status === 'rebuilding') {
                    this.showToast("Rebuilding project index...", "info");
                    const interval = setInterval(() => {
                        fetch('/api/index-status')
                            .then(res => res.json())
                            .then(status => {
                                if (status.is_valid) {
                                    clearInterval(interval);
                                    this.fetchStructure(); // Reload structure instead of page reload
                                    this.showToast("Index rebuilt successfully", "success");
                                }
                            })
                            .catch(err => console.error('Status check failed:', err));
                    }, 1000);
                }
            })
            .catch(error => {
                console.error('Error rebuilding index:', error);
                this.showToast('Failed to rebuild index', 'error');
            });
    }

    filterToDirectory(path) {
        const escapedPath = this.escapeRegex(path);
        const regexPattern = path ? `^${escapedPath}/.*` : '^.*';
        this.elements.fileFilter.value = regexPattern;
        this.elements.regexModeCheckbox.checked = true;
        this.isRegexMode = true;
        this.filterText = regexPattern;
        this.applyFilter();
    }

    highlightMatch(element, text, filterText) {
        if (!filterText) {
            element.textContent = text;
            return;
        }
        const lowerText = text.toLowerCase();
        const filterLower = filterText.toLowerCase();
        const index = lowerText.indexOf(filterLower);
        if (index >= 0) {
            const before = text.substring(0, index);
            const match = text.substring(index, index + filterText.length);
            const after = text.substring(index + filterText.length);
            element.innerHTML = `${this.escapeHtml(before)}<span class="bg-yellow-200 font-bold">${this.escapeHtml(match)}</span>${this.escapeHtml(after)}`;
        } else {
            element.textContent = text;
        }
    }

    escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    capitalizeFirstLetter(string) {
        if (!string) return string;
        return string.charAt(0).toUpperCase() + string.slice(1);
    }

    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        let bgClass = 'bg-blue-600';
        if (type === 'success') bgClass = 'bg-green-600';
        if (type === 'error') bgClass = 'bg-red-600';

        toast.className = `${bgClass} text-white px-4 py-3 rounded-lg shadow-lg flex items-center justify-between max-w-sm mb-2 transform transition-all duration-300 ease-out translate-x-full opacity-0 pointer-events-auto`;

        toast.innerHTML = `
            <span class="mr-2">${message}</span>
            <button class="ml-2 hover:bg-white hover:bg-opacity-20 rounded-full p-1 focus:outline-none">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        `;

        const closeBtn = toast.querySelector('button');
        closeBtn.onclick = () => {
            toast.classList.add('translate-x-full', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        };

        this.elements.toastContainer.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove('translate-x-full', 'opacity-0');
        });

        // Auto dismiss
        setTimeout(() => {
            toast.classList.add('translate-x-full', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    saveSelections() {
        if (!this.projectName) return;
        const key = `contextCreatorSelectedPaths_${this.projectName}`;
        localStorage.setItem(key, JSON.stringify(Array.from(this.selectedPaths)));
    }

    loadSelections() {
        if (!this.projectName) return;
        const key = `contextCreatorSelectedPaths_${this.projectName}`;
        const saved = localStorage.getItem(key);
        if (saved) {
            try {
                const paths = JSON.parse(saved);
                paths.forEach(path => {
                     // Verify path still exists in structure before adding
                     const node = this.findNodeByPath(this.projectStructure, path);
                     if (node && node.type === 'file') {
                         this.selectedPaths.add(path);
                     }
                });
            } catch (e) {
                console.error('Failed to load selections:', e);
            }
        }
        this.updateCheckboxStates();
        this.updateSelectionCounter();
    }
}
