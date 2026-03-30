import os
import json
import time
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
    
    # 1. SPOOF GOOGLEBOT: Tricks many paywalls into showing full content
    chrome_options.add_argument("user-agent=Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
    
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
                # 2. REFERER SPOOF: Pretend we are coming from a social search
                driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
                    "headers": {"Referer": "https://www.google.com/"}
                })
                
                driver.get(link)
                time.sleep(5)
                
                # 3. DELETE PAYWALL VIA JAVASCRIPT
                # This removes the iframe container you identified before it can block the view
                driver.execute_script("""
                    var paywall = document.getElementById('arthardpv');
                    if (paywall) { paywall.remove(); }
                    var ads = document.querySelectorAll('.article-ad, .dfp-ad');
                    ads.forEach(ad => ad.remove());
                """)

                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                
                try:
                    img_el = driver.find_element(By.CSS_SELECTOR, 'div.article-picture img, [itemprop="articleBody"] img')
                    img_url = img_el.get_attribute("data-src-template") or img_el.get_attribute("src")
                except: img_url = None

                # Extracting all paragraphs and headings from the schemaDiv you provided
                # We target only the children of .schemaDiv to avoid related stories
                body_container = driver.find_element(By.CSS_SELECTOR, '.schemaDiv[itemprop="articleBody"]')
                text_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h4.sub_head")
                
                article_content = []
                for el in text_elements:
                    text = el.text.strip()
                    if not text or any(x in text for x in ["Related Stories", "mukunth.v@", "| Photo Credit:"]):
                        continue
                    
                    article_content.append({
                        "type": "heading" if el.tag_name == "h4" else "text",
                        "value": text
                    })

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

# --- TARGETS AND SAVE LOGIC REMAINS THE SAME ---
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
    new_arts = scrape_section(url, cat)
    urls = [a['url'] for a in full_db]
    for art in new_arts:
        if art['url'] not in urls: full_db.insert(0, art)
with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:500], f, ensure_ascii=False, indent=4)
