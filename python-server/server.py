from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from transformers import pipeline, AutoTokenizer
from keybert import KeyBERT
import nltk
import re
from urllib.parse import urlparse
from googlesearch import search 
from concurrent.futures import ThreadPoolExecutor
import webCrawler
import time
import csv

app = Flask(__name__)
CORS(app)

# Download necessary NLTK data
# nltk.download('punkt')
# nltk.download('stopwords')

# Initialize the summarization pipeline
model_name = 'pszemraj/long-t5-tglobal-base-16384-book-summary'
summarizer = pipeline('summarization', model=model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Define chunk size
chunk_size = min(tokenizer.model_max_length, 3000)

def log_to_csv(original_url, num_relevant_links, crawl_time, visited_links_count, avg_similarity,filename='crawl_log.csv'):
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        # Write header only if file is empty
        if file.tell() == 0:
            writer.writerow(['Original URL', 'Number of relevant Links','Average Similarity', 'Crawl Time','Number of Visted Links'])
        writer.writerow([original_url, num_relevant_links, avg_similarity, crawl_time,visited_links_count])

def preprocess_text(text):
    text = re.sub(r'\s+', ' ', text)
    sentences = nltk.tokenize.sent_tokenize(text)
    return "\n".join(sentences)

def chunk_text(text, chunk_size):
    sentences = nltk.tokenize.sent_tokenize(text)
    chunks, current_chunk = [], ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += " " + sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

# extracting article from html
def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # List of unwanted classes
    unwanted_classes = ['navigation', 'reflist', 'catlinks']
    
    # Remove elements with the specified classes
    for unwanted_class in unwanted_classes:
        for unwanted in soup.find_all(class_=unwanted_class):
            unwanted.decompose()  # Remove element and its children

    # Remove header, footer, comments, sidebar, and advertisements by tag
    tags_to_remove = ['header', 'footer', 'aside']
    for tag in tags_to_remove:
        for unwanted_tag in soup.find_all(tag):
            unwanted_tag.decompose()

    # Find main content area (adjust based on actual HTML structure)
    main_content = soup.find('article') or soup.find('main') or soup.find('div', class_='post')

    if not main_content:
        main_content = soup.body  # Fallback to the entire body if specific tags are not found

    # Extract relevant content from the identified section
    relevant_content = []
    for tag in main_content.find_all(['h2', 'p', 'li'], recursive=True):  # Specify the tags to search
        text_content = tag.get_text().strip()
        if text_content and len(text_content) > 20:  # Filter out short texts
            relevant_content.append(f"{text_content}")

    return ' '.join(relevant_content)
def extract_keywords(text, num_keywords=4):
    kw_model = KeyBERT()
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words=None)
    return [keyword for keyword, _ in keywords]

def perform_search(query):
    return list(search(query, num_results=5))

def google_dork_search(keywords, num_results=5):
    queries = [f'"{keyword}"' for keyword in keywords]
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(perform_search, queries))
    # Flatten the list of results from different queries
    search_results = [item for sublist in results for item in sublist]
    return search_results[:num_results]  # Limit to top results

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.json
    html_content = data.get('html', '')
    original_url = data.get('url','')
    print("Starting..........")
    # Clean HTML to get only paragraph content
    cleaned_text = clean_html(html_content)
    
    # Preprocess and chunk the text
    preprocessed_text = preprocess_text(cleaned_text)
    text_chunks = chunk_text(preprocessed_text, chunk_size)
    
    # Summarize each chunk
    summaries = []
    for chunk in text_chunks:
        result = summarizer(chunk, max_length=512, min_length=100, do_sample=False)
        summaries.append(result[0]['summary_text'])
    
    # Combine summaries
    full_summary = " ".join(summaries)
    final_summary = full_summary.replace("Victor", "author").replace("Tommo", "author").replace("chapter", "article").replace("lesson","article")
    # print(final_summary)
    # Extract keywords from the summary
    keywords = extract_keywords(preprocessed_text, num_keywords=3)
    # print(keywords)
    # Get initial seed URLs from Google search
    start_time = time.time()
    seed_urls = google_dork_search(keywords, num_results=10)
    # print(seed_urls)
    # Use the crawler to find relevant pages
    relevant_links, visited_links_count,avg_similarity = webCrawler.get_relevant_links(seed_urls, cleaned_text)
    # print(relevant_links)
    end_time = time.time()
    elapsed_time = end_time - start_time
    num_relevant_links = len(relevant_links)
    print(f"Time taken for the process: {elapsed_time:.2f} seconds")

    # Log data to CSV
    log_to_csv(original_url, num_relevant_links, elapsed_time,visited_links_count,avg_similarity)

    return jsonify({
        'summary': final_summary,
        'keywords': keywords,
        'top_links': relevant_links
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)