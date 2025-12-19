function getAuthHeaders() {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    const issuedAt = localStorage.getItem('issued_at');
    
    if (!token || !username || !issuedAt) {
        window.location.href = 'index.html';
        return null;
    }
    
    return {
        "X-Token": token,
        "X-Issued-Date": issuedAt,
        "X-Username": username
    };
}

function getUsername() {
    return localStorage.getItem('username') || '';
}

function isAuthenticated() {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    const issuedAt = localStorage.getItem('issued_at');
    return !!(token && username && issuedAt);
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('issued_at');
    window.location.href = 'index.html';
}
