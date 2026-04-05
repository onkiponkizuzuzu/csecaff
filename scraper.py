import os
import json
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Load existing database to check for duplicates early
data_file = "data.json"
if os.path.exists(data_file):
    with open(data_file, "r", encoding='utf-8') as f:
        full_db = json.load(f)
else:
    full_db = []

# Create a set of existing URLs for O(1) lookups
existing_urls = {art['url'] for art in full_db}

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Use standard Chrome driver for GitHub Runner
    driver = webdriver.Chrome(options=chrome_options)
    
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*",
            "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"
        ]
    })
    driver.set_page_load_timeout(180)
    return driver

# ================== The Hindu Scraper ==================
def scrape_hindu_section(url, category):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = list(set([el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article" in el.get_attribute("href")]))
        
        # Only scrape links not in database
        new_links = [l for l in links if l not in existing_urls]

        for link in new_links:
            try:
                driver.get(link)
                time.sleep(5)
                body_container = driver.find_element(By.CSS_SELECTOR, 'div.schemaDiv[itemprop="articleBody"]')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h4.sub_head")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    if not text or any(x in text for x in ["Related Stories", "mukunth.v@", "| Photo Credit:"]):
                        continue
                    article_content.append({"type": "heading" if el.tag_name == "h4" else "text", "value": html_content})

                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                if len(article_content) > 1:
                    articles.append({
                        "category": category, "title": title, "url": link, "content": article_content, "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except: continue
    finally: driver.quit()
    return articles

# ================== Indian Express Scraper ==================
def scrape_ie_section(url, category):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = list(set([el.get_attribute("href") for el in elements if el.get_attribute("href") and "/article/upsc-current-affairs/" in el.get_attribute("href")]))
        
        new_links = [l for l in links if l not in existing_urls]

        for link in new_links:
            try:
                driver.get(link)
                time.sleep(6)
                driver.execute_script("const content = document.getElementById('pcl-full-content'); if (content) content.style.display = 'block';")

                body_container = driver.find_element(By.ID, "pcl-full-content")
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    html_content = el.get_attribute('innerHTML').strip()
                    if not text or any(skip in text for skip in ["Subscriber Only", "ALSO READ", "Subscribe"]):
                        continue
                    article_content.append({"type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text", "value": html_content})

                title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                if len(article_content) > 3:
                    articles.append({
                        "category": category, "title": title, "url": link, "content": article_content, "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except: continue
    finally: driver.quit()
    return articles

# ================== Indian Express Quizzes Scraper ==================
def scrape_ie_quizzes(category="UPSC Quizzes", pages=20):
    driver = get_driver()
    articles = []
    base_url = "https://indianexpress.com/section/upsc-current-affairs/page/"
    try:
        for page in range(1, pages + 1):
            driver.get(f"{base_url}{page}/")
            time.sleep(6)
            elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
            
            links = []
            for el in elements:
                href = el.get_attribute("href")
                if href and "/article/upsc-current-affairs/" in href and "Daily subject-wise quiz" in el.text:
                    if href not in existing_urls:
                        links.append(href)
            
            if not links:
                print(f"No new quizzes found on page {page}. Ending search.")
                break

            for link in list(set(links)):
                try:
                    driver.get(link)
                    time.sleep(6)
                    driver.execute_script("const content = document.getElementById('pcl-full-content'); if (content) content.style.display = 'block';")
                    body_container = driver.find_element(By.ID, "pcl-full-content")
                    content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                    
                    article_content = []
                    current_q = None
                    for el in content_elements:
                        text = el.text.strip()
                        html_content = el.get_attribute('innerHTML').strip()
                        if not text or "Subscriber Only" in text: continue
                        
                        if "QUESTION" in text.upper():
                            if current_q: article_content.append(current_q)
                            current_q = {"type": "quiz_item", "question": f"<p>{html_content}</p>", "solution": ""}
                        elif current_q:
                            if any(x in text for x in ["Explanation:", "Correct Answer", "Answer:"]) or current_q["solution"] != "":
                                current_q["solution"] += f"<p>{html_content}</p>"
                            else:
                                current_q["question"] += f"<p>{html_content}</p>"
                        else:
                            article_content.append({"type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text", "value": html_content})

                    if current_q: article_content.append(current_q)
                    title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                    articles.append({
                        "category": category, "title": title, "url": link, "content": article_content, "date": datetime.now().strftime("%Y-%m-%d")
                    })
                except: continue
    finally: driver.quit()
    return articles

# ================== Main Execution ==================
targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/",
    "UPSC Current Affairs": "https://indianexpress.com/section/upsc-current-affairs/"
}

for cat, url in targets.items():
    print(f"Processing {cat}...")
    new_arts = scrape_ie_section(url, cat) if cat == "UPSC Current Affairs" else scrape_hindu_section(url, cat)
    for art in new_arts:
        if art['url'] not in existing_urls:
            full_db.insert(0, art)
            existing_urls.add(art['url'])

print("Processing UPSC Quizzes...")
quiz_arts = scrape_ie_quizzes("UPSC Quizzes", pages=20)
for art in quiz_arts:
    if art['url'] not in existing_urls:
        full_db.insert(0, art)
        existing_urls.add(art['url'])

# Save JSON (Keep latest 1000)
with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:1000], f, ensure_ascii=False, indent=4)

print(f"Scrape completed. Total database size: {len(full_db)}")
