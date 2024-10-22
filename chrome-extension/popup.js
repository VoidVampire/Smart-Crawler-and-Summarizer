document.getElementById('summarizeBtn').addEventListener('click', () => {
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, {action: "getHTML"}, (response) => {
        if (response && response.html) {
          fetch('http://localhost:5000/summarize', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({html: response.html}),
          })
          .then(response => response.json())
          .then(data => {
            document.getElementById('summary').textContent = data.summary;
            document.getElementById('keywords').textContent = 'Keywords: ' + data.keywords.join(', ');

            // Display top links
            const topLinksContainer = document.getElementById('topLinks');
            topLinksContainer.innerHTML = ''; // Clear previous links
            data.top_links.forEach(link => {
              const linkElement = document.createElement('a');
              linkElement.href = link;
              linkElement.textContent = link;
              linkElement.target = '_blank'; // Open links in a new tab
              topLinksContainer.appendChild(linkElement);
            });
          })
          .catch((error) => {
            console.error('Error:', error);
            document.getElementById('summary').textContent = 'Error: Could not connect to the summarization server.';
          });
        }
      });
    });
  });
