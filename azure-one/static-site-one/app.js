function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fi-FI', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatRSSLoadDate(dateString) {
    const date = new Date(dateString);
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `Ladattu klo ${hours}:${minutes} - ${day}.${month}.${year}`;
}

function isRSSFeedOld(dateString, hoursThreshold = 8) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = diffMs / (1000 * 60 * 60);
    return diffHours >= hoursThreshold;
}

function renderHeader() {
    const username = getUsername();
    const header = document.querySelector('header');
    if (header) {
        const usernameEl = header.querySelector('.username');
        if (usernameEl) {
            usernameEl.textContent = username;
        }
    }
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    document.body.insertBefore(errorDiv, document.body.firstChild);
    
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

function showLoading(element) {
    element.innerHTML = '<div class="loading">Loading...</div>';
}

function hideLoading(element) {
    const loading = element.querySelector('.loading');
    if (loading) {
        loading.remove();
    }
}
