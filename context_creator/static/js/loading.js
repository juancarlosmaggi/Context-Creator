function showError(message) {
    const loader = document.querySelector('.loader');
    const title = document.getElementById('loading-title');
    const detail = document.getElementById('loading-message');
    const error = document.getElementById('loading-error');

    if (loader) loader.classList.add('hidden');
    if (title) title.textContent = 'Failed to build project index';
    if (detail) {
        detail.textContent = 'Token indexing could not start because tiktoken failed to initialize.';
    }
    if (error) {
        error.textContent = message;
        error.classList.remove('hidden');
    }
}

// Check index status every second
function checkStatus() {
    fetch('/api/index-status')
        .then(response => response.json())
        .then(data => {
            if (data.is_valid) {
                window.location.reload();
            } else if (data.error) {
                showError(data.error);
            } else {
                // Keep checking until valid
                setTimeout(checkStatus, 1000);
            }
        });
}

// Start checking immediately
checkStatus();
