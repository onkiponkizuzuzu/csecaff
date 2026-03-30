import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_section(url, category):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/google-chrome"
    
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    articles = []
    try:
        driver.get(url)
        time.sleep(8) # Allow main page to load
        
        elements = driver.find_elements(By.CSS_SELECTOR, "h3[class*='title'] a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))

        for link in links[:12]:
            try:
                driver.get(link)
                # Wait for content to exist but scrape before the paywall fully locks
                wait = WebDriverWait(driver, 12)
                body_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[itemprop="articleBody"]')))
                
                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                
                try:
                    img_el = driver.find_element(By.CSS_SELECTOR, 'div.article-picture img, [itemprop="articleBody"] img')
                    img_url = img_el.get_attribute("data-src-template") or img_el.get_attribute("src")
                except: img_url = None

                # Capture only the narrative tags to skip ad-containers and related story blocks
                text_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h1, h2, h3, h4")
                
                article_content = []
                for el in text_elements:
                    tag = el.tag_name
                    text = el.text.strip()
                    
                    # Filtering out the 'junk' rows we identified
                    if not text or "Related Stories" in text or "mukunth.v@" in text or "| Photo Credit:" in text:
                        continue
                    
                    el_type = "heading" if tag.startswith("h") else "text"
                    article_content.append({"type": el_type, "value": text})

                if len(article_content) > 1: # Validation check
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
