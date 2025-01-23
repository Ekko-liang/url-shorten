async function shortenUrl() {
    const urlInput = document.getElementById('urlInput');
    const shortUrlElement = document.getElementById('shortUrl');
    const copyButton = document.getElementById('copyButton');
    const url = urlInput.value;

    if (!url) {
        alert('Please enter a URL');
        return;
    }

    try {
        const response = await fetch('/shorten', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();
        
        if (response.ok) {
            shortUrlElement.textContent = data.short_url;
            copyButton.style.display = 'inline-block';
        } else {
            shortUrlElement.textContent = 'Error: ' + data.error;
            copyButton.style.display = 'none';
        }
    } catch (error) {
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
        alert('Failed to copy to clipboard');
    }
}
