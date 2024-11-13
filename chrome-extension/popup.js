document.getElementById("startBtn").addEventListener("click", () => {
  document.getElementById("summarizeBtn").click();
  document.getElementById("crawlButton").click();
})

document.getElementById("crawlButton").addEventListener("click", () => {
  console.log("Clicked")
  const loadingElement = document.getElementById("crawlLoading");
  const spinner = document.getElementById("crawlLoadingSpinner");
  const topLinksElement = document.getElementById("topL");
  
  loadingElement.style.display = "block";
  spinner.style.display = "block";
  document.getElementById("crawlError").textContent = "";

  chrome.tabs.query({ active: true, currentWindow: true}, (tabs) => {
    const currentTab = tabs[0];
    const tabUrl = currentTab.url;
    
    chrome.storage.local.get([tabUrl], (result) => {

      chrome.tabs.sendMessage(tabs[0].id, {action: "getHTML"}, (response) => {
        if(response && response.html){
          fetch("http:localhost:5000/crawl", {
            method: "POST",
            headers: {
              "Content-type": "application/json",
            },
            body: JSON.stringify({html: response.html, url: tabUrl})
          })
          .then((response) => response.json())
          .then((data) => {
            loadingElement.style.display = "none";
            spinner.style.display = "none";
            topLinksElement.style.display = "block";
            displayLinks(data.keywords, data.top_links)
          })
          .catch((error) => {
            loadingElement.style.display = "none";
            spinner.style.display = "none";
            console.log(error);
            document.getElementById("crawlError").textContent = "Error: Could not connect to the summarization server.";
            document.getElementById("keywords").textContent = "";
            document.getElementById("topL").style.display = "none";
            document.getElementById("topLinks").textContent = "";
          })
        }
      })

    })
  })
  
})

document.getElementById("summarizeBtn").addEventListener("click", () => {
  const loadingElement = document.getElementById("summaryLoading");
  const spinner = document.getElementById("summaryLoadingSpinner");

  loadingElement.style.display = "block";
  spinner.style.display = "block";
  document.getElementById("summaryError").textContent = "";

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const currentTab = tabs[0];
    const tabUrl = currentTab.url;

    chrome.storage.local.get([tabUrl], (result) => {
      if (result[tabUrl]) {
        const storedData = result[tabUrl];
        loadingElement.style.display = "none";
        spinner.style.display = "none";
        displaySummary(storedData.summary);
      }
      else {
      chrome.tabs.sendMessage(tabs[0].id, { action: "getHTML" }, (response) => {
        if (response && response.html) {
          fetch("http://localhost:5000/summarize", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ html: response.html, url: tabUrl }),
          })
            .then((response) => response.json())
            .then((data) => {
              loadingElement.style.display = "none";
              spinner.style.display = "none";
              chrome.storage.local.set({
                [tabUrl]: {
                  summary: data.summary,
                },
              });
              displaySummary(data.summary);
            })
            .catch((error) => {
              loadingElement.style.display = "none";
              spinner.style.display = "none";
              console.error("Error:", error);
              document.getElementById("SummaryError").textContent =
                "Error: Could not connect to the summarization server.";
            });
        }
      });
      }
    });
  });
});

function displaySummary(summary) {
  const summaryElement = document.getElementById("summary");
  summaryElement.textContent = summary;
}

function displayLinks(keywords, top_links){
  // const keywordsElement = document.getElementById("keywords");
  const topLinksContainer = document.getElementById("topLinks");
  document.getElementById("topL").style.display = "block";

  // keywordsElement.textContent = "Keywords: " + keywords.join(", ");

  topLinksContainer.innerHTML = "";
  top_links.forEach((link) => {
    const linkElement = document.createElement("a");
    linkElement.href = link;
    linkElement.textContent = link;
    linkElement.target = "_blank";
    topLinksContainer.appendChild(linkElement);
  });
}