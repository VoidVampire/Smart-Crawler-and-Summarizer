# Smart Crawler and Summarizer

A powerful tool combining a Chrome Extension frontend with a Flask server backend to perform web crawling and summarization tasks efficiently. It uses technologies like **BeautifulSoup**, **KeyBERT**, **Google Search API**, and **Hugging Face Transformers** for web crawling and summarization.

## Project Structure

### 1. **Chrome Extension** (`chrome-extension`)
   - Acts as the frontend.
   - Allows users to interact with the crawler and summarizer.
   - **Usage**: Add this extension in Chrome by enabling **Developer Mode** in the Chrome extensions page and loading the unpacked folder.

### 2. **Python Server** (`python-server`)
   - Backend server built with Flask.
   - Handles web crawling and summarization requests through defined API endpoints.
   - **Core files**:
     - `server.py`: The main Flask application, which processes requests and orchestrates tasks like crawling and summarization.
     - `webCrawler.py`: Implements an asynchronous, relevance-based web crawler.

---

## Features

### Web Crawler
- Utilizes `BeautifulSoup` and `aiohttp` for efficient web crawling.
- Filters irrelevant content using cosine similarity via `TfidfVectorizer`.
- Extracts meaningful content from visited web pages.

### Summarization
- Uses Hugging Face's Long T5 model for text summarization.
- Processes large content efficiently by dividing it into manageable chunks and implementing multiprocessing.

### Keyword Extraction
- Extracts top keywords using **KeyBERT**, aiding in refining search queries.

---


## Installation

### 1. Clone the repository:
```bash
git clone https://github.com/<your-username>/smart-crawler-summarizer.git
cd smart-crawler-summarizer
```

### 2. Install dependencies:
```bash
cd python-server
pip install -r requirements.txt
```

### 3. Run the Flask server:
```bash
cd python-server
python server.py
```
The server will run on **`http://127.0.0.1:5000`**.

---

## Usage

1. **Set up the Chrome Extension**:
   - Go to Chrome settings → Extensions → Enable Developer Mode.
   - Click "Load unpacked" and select the `chrome-extension` folder.

2. **Run the Server**:
   - Start the Flask server as explained in the [Installation](#installation) section.

3. **Use Extension**:
   - Open any article link, click on the extension, and click on 'Summarize Article' button or 'Get Relevant Links' or 'Generate Both'.

---

## Technologies Used
- **Backend**: Flask, aiohttp, BeautifulSoup
- **Frontend**: Chrome Extension
- **Libraries**: Hugging Face Transformers, KeyBERT, NLTK
- **Crawler**: Asynchronous web crawling with relevance filtering
