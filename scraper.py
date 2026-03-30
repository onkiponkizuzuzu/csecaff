import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def scrape_section(url, category):
    # SETTING UP GITHUB-COMPATIBLE CHROME
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/google-chrome"
    
    # Using standard service for GitHub Ubuntu runner
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    articles = []
    try:
        driver.get(url)
        time.sleep(10) # Longer wait for GitHub runner latency
        
        elements = driver.find_elements("css selector", "h3[class*='title'] a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))

        for link in links[:8]: # Reduced limit for first successful test
            try:
                driver.get(link)
                time.sleep(4)
                title = driver.find_element("css selector", "h1.title").text.strip()
                
                try:
                    img_el = driver.find_element("css selector", 'div.article-picture img, [itemprop="articleBody"] img')
                    img_url = img_el.get_attribute("data-src-template") or img_el.get_attribute("src")
                except: img_url = None

                body = driver.find_element("css selector", '[itemprop="articleBody"]')
                paras = body.find_elements("css selector", "p")
                article_content = [{"type": "text", "value": p.text.strip()} for p in paras if p.text.strip() and "| Photo Credit:" not in p.text]

                articles.append({
                    "category": category,
                    "title": title,
                    "url": link,
                    "image": img_url,
                    "content": article_content,
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
            except: continue
    finally:
        driver.quit()
    return articles

# --- REST OF THE SCRIPT (TARGETS & SAVE LOGIC) REMAINS THE SAME ---
targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/"
}

data_file = "data.json"
if os.path.exists(data_file):
    with open(data_file, "r") as f:
        full_db = json.load(f)
else:
    full_db = []

for cat, url in targets.items():
    print(f"Scraping {cat}...")
    new_articles = scrape_section(url, cat)
    existing_urls = [a['url'] for a in full_db]
    for art in new_articles:
        if art['url'] not in existing_urls:
            full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:500], f, ensure_ascii=False, indent=4)
