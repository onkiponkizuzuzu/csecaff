import os
import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
        time.sleep(8)
        
        elements = driver.find_elements(By.CSS_SELECTOR, "h3[class*='title'] a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))

        for link in links[:12]:
            try:
                driver.get(link)
                time.sleep(5)
                
                # --- MASTER FIX: EXTRACT FROM JSON-LD METADATA ---
                # We look for the script tag that contains the SEO 'NewsArticle' schema
                scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
                full_text = ""
                
                for script in scripts:
                    try:
                        content = json.loads(script.get_attribute('innerHTML'))
                        # The Hindu stores the full narrative in 'articleBody'
                        if isinstance(content, dict) and 'articleBody' in content:
                            full_text = content['articleBody']
                            break
                        elif isinstance(content, list):
                            for item in content:
                                if 'articleBody' in item:
                                    full_text = item['articleBody']
                                    break
                    except: continue

                # If Metadata extraction failed, fallback to visible P tags
                if not full_text:
                    p_tags = driver.find_elements(By.CSS_SELECTOR, '.schemaDiv[itemprop="articleBody"] p')
                    full_text = "\n\n".join([p.text for p in p_tags])

                # Cleaning the text into our structured format
                # We split the long metadata string into paragraphs based on double newlines
                paragraphs = re.split(r'\n\n|\n', full_text)
                article_content = []
                for p in paragraphs:
                    clean_p = p.strip()
                    if clean_p and not any(x in clean_p for x in ["Related Stories", "mukunth.v@", "| Photo Credit:"]):
                        article_content.append({"type": "text", "value": clean_p})

                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                
                try:
                    img_el = driver.find_element(By.CSS_SELECTOR, 'div.article-picture img, [itemprop="articleBody"] img')
                    img_url = img_el.get_attribute("data-src-template") or img_el.get_attribute("src")
                except: img_url = None

                if len(article_content) > 0:
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

# --- TARGETS AND BATCH LOGIC (Same as before) ---
targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/"
}

data_file = "data.json"
full_db = json.load(open(data_file)) if os.path.exists(data_file) else []
for cat, url in targets.items():
    print(f"Scraping {cat}...")
    new_arts = scrape_section(url, cat)
    urls = [a['url'] for a in full_db]
    for art in new_arts:
        if art['url'] not in urls: full_db.insert(0, art)
with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:500], f, ensure_ascii=False, indent=4)
