// Main JavaScript for Lode
// Minimal vanilla JS - HTMX handles most interactions

// Format timestamps
function formatTime(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

// Format message content (basic markdown-like rendering)
function formatMessage(content) {
    // Escape HTML
    let html = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // Code blocks
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Links
    html = html.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Lode initialized');
});

