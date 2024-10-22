chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'fetchHTML') {
      console.log("Received HTML content from content script, sending to Python API...");
  
      // Send the HTML content to the Python server for summarization
      fetch('http://127.0.0.1:5000/summarize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ html: message.html })  // Send the article as JSON
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        return response.json();  // Parse the JSON response (should contain the summary)
      })
      .then(data => {
        console.log("Received summary from Python API:", data.summary);  // Debugging summary
  
        // Send the summary to the popup or content script for display
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          chrome.tabs.sendMessage(tabs[0].id, {
            action: 'displaySummary',
            summary: data.summary  // Send the summary to be displayed
          });
        });
      })
      .catch(error => {
        console.error("Error during API request:", error);  // Catch and log any errors
      });
  
      // Return true to signal that async processing is ongoing
      return true;
    }
  });
  