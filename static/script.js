async function shortenUrl() {
    const urlInput = document.getElementById('urlInput');
    const shortUrlElement = document.getElementById('shortUrl');
    const copyButton = document.getElementById('copyButton');
    const url = urlInput.value.trim();

    if (!url) {
        alert('Please enter a URL');
        return;
    }

    // Add http:// if no protocol is specified
    const finalUrl = url.startsWith('http://') || url.startsWith('https://') ? url : `https://${url}`;

    try {
        const response = await fetch('/shorten', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: finalUrl })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.short_url) {
            shortUrlElement.textContent = data.short_url;
            copyButton.style.display = 'inline-block';
        } else {
            throw new Error('No short URL in response');
        }
    } catch (error) {
        console.error('Error:', error);
        shortUrlElement.textContent = 'Error: Could not shorten URL';
        copyButton.style.display = 'none';
    }
}

async function copyToClipboard() {
    const shortUrl = document.getElementById('shortUrl').textContent;
    try {
        await navigator.clipboard.writeText(shortUrl);
        alert('Copied to clipboard!');
    } catch (err) {
        console.error('Failed to copy:', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = shortUrl;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            alert('Copied to clipboard!');
        } catch (err) {
            console.error('Fallback copy failed:', err);
            alert('Failed to copy to clipboard');
        }
        document.body.removeChild(textArea);
    }
}
