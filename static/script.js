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
        console.log('Sending request with URL:', finalUrl);  // Debug log
        const response = await fetch('/shorten', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: finalUrl })
        });

        console.log('Response status:', response.status);  // Debug log
        const responseText = await response.text();
        console.log('Response text:', responseText);  // Debug log

        let data;
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error('Failed to parse response:', e);
            throw new Error(`Invalid response format: ${responseText}`);
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}, message: ${data.error || responseText}`);
        }

        if (data.short_url) {
            shortUrlElement.textContent = data.short_url;
            copyButton.style.display = 'inline-block';
        } else {
            throw new Error('No short URL in response');
        }
    } catch (error) {
        console.error('Error details:', error);  // Debug log
        shortUrlElement.textContent = `Error: ${error.message}`;
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
