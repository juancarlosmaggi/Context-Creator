// Check index status every second
function checkStatus() {
    fetch('/api/index-status')
        .then(response => response.json())
        .then(data => {
            if (data.is_valid) {
                window.location.reload();
            } else {
                // Keep checking until valid
                setTimeout(checkStatus, 1000);
            }
        });
}

// Start checking immediately
checkStatus();
