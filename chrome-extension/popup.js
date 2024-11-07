document.getElementById("summarizeBtn").addEventListener("click", () => {
  const loadingElement = document.getElementById("loading");
  const spinner = document.getElementById("loadingSpinner");
  const topLinkElement = document.getElementById("topL");

  loadingElement.style.display = "block";
  spinner.style.display = "block";
  document.getElementById("error").textContent = "";

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const currentTab = tabs[0];
    const tabUrl = currentTab.url;

    chrome.storage.local.get([tabUrl], (result) => {
      // if (result[tabUrl]) {
      //   const storedData = result[tabUrl];
      //   loadingElement.style.display = "none";
      //   spinner.style.display = "none";
      //   displaySummaryAndLinks(
      //     storedData.summary,
      //     storedData.keywords,
      //     storedData.top_links
      //   );
      // } 
      // else {
        chrome.tabs.sendMessage(
          tabs[0].id,
          { action: "getHTML" },
          (response) => {
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
                  topLinkElement.style.display = "block";
                  chrome.storage.local.set({
                    [tabUrl]: {
                      summary: data.summary,
                      keywords: data.keywords,
                      top_links: data.top_links,
                    },
                  });
                  displaySummaryAndLinks(
                    data.summary,
                    data.keywords,
                    data.top_links
                  );
                })
                .catch((error) => {
                  loadingElement.style.display = "none";
                  spinner.style.display = "none";
                  console.error("Error:", error);
                  document.getElementById("error").textContent =
                    "Error: Could not connect to the summarization server.";
                  document.getElementById("keywords").textContent = "";
                  document.getElementById("topL").style.display = "none";
                  document.getElementById("topLinks").textContent = "";
                });
            }
          }
        );
      // }
    });
  });
});

function displaySummaryAndLinks(summary, keywords, top_links) {
  const summaryElement = document.getElementById("summary");
  const keywordsElement = document.getElementById("keywords");
  const topLinksContainer = document.getElementById("topLinks");
  document.getElementById("topL").style.display="block";

  summaryElement.textContent = summary;

  keywordsElement.textContent = "Keywords: " + keywords.join(", ");

  topLinksContainer.innerHTML = "";
  top_links.forEach((link) => {
    const linkElement = document.createElement("a");
    linkElement.href = link;
    linkElement.textContent = link;
    linkElement.target = "_blank"; 
    topLinksContainer.appendChild(linkElement);
  });
}
