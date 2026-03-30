import google_colab_selenium as gs
import json
import os
from datetime import datetime
import time

def scrape_section(url, category):
    driver = gs.Chrome()
    articles = []
    try:
        driver.get(url)
        time.sleep(5)
        # Capture links from both the featured grid and the main list
        elements = driver.find_elements("css selector", "h3[class*='title'] a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))

        for link in links[:12]: # Limit to top 12 per section for stability
            try:
                driver.get(link)
                time.sleep(3)
                title = driver.find_element("css selector", "h1.title").text.strip()
                
                # Image Extraction
                try:
                    img_el = driver.find_element("css selector", 'div.article-picture img, [itemprop="articleBody"] img')
                    img_url = img_el.get_attribute("data-src-template") or img_el.get_attribute("src")
                except: img_url = None

                # Content Extraction (Cleaning based on your preferences)
                body = driver.find_element("css selector", '[itemprop="articleBody"]')
                paras = body.find_elements("css selector", "p")
                article_content = []
                for p in paras:
                    txt = p.text.strip()
                    if txt and "| Photo Credit:" not in txt:
                        article_content.append({"type": "text", "value": txt})

                articles.append({
                    "category": category,
                    "title": title,
                    "url": link,
                    "image": img_url,
                    "content": article_content,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M")
                })
            except: continue
    finally:
        driver.quit()
    return articles

targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/"
}

# Load existing data if it exists
data_file = "data.json"
if os.path.exists(data_file):
    with open(data_file, "r") as f:
        full_db = json.load(f)
else:
    full_db = []

# Scrape and Append
for cat, url in targets.items():
    print(f"Scraping {cat}...")
    new_articles = scrape_section(url, cat)
    # Add only if URL is not already in database (Deduplication)
    existing_urls = [a['url'] for a in full_db]
    for art in new_articles:
        if art['url'] not in existing_urls:
            full_db.insert(0, art) # Add new ones to the top

# Keep only the latest 500 articles to prevent file bloating
full_db = full_db[:500]

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db, f, ensure_ascii=False, indent=4)
