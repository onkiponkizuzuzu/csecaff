import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager   # ← New

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")          # Modern headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")

    # Let webdriver-manager handle the driver
    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=chrome_options)

    # CDP: Block paywall / tracking scripts early
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*", "*doubleclick.net*"]
    })

    driver.set_page_load_timeout(180)
    return driver


def scrape_section(url, category):
    driver = get_driver()
    articles = []
    try:
        driver.get(url)
        time.sleep(10)   # Increased wait for dynamic content

        # Get unique article links
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a, article a")
        links = list(set([
            el.get_attribute("href") 
            for el in elements 
            if el.get_attribute("href") and "/article" in el.get_attribute("href")
        ]))

        for link in links[:10]:   # Limit per category to avoid timeout
            try:
                driver.get(link)
                time.sleep(6)

                # Main article body
                body_container = driver.find_element(By.CSS_SELECTOR, 'div.schemaDiv[itemprop="articleBody"], article')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")

                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    if not text or any(skip in text for skip in ["Related Stories", "mukunth.v@", "Photo Credit", "©"]):
                        continue
                    article_content.append({
                        "type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text",
                        "value": text
                    })

                title = driver.find_element(By.CSS_SELECTOR, "h1.title, h1").text.strip()

                # Image handling
                try:
                    img_el = driver.find_element(By.CSS_SELECTOR, 'div.article-picture img, [itemprop="articleBody"] img, figure img')
                    img_url = (img_el.get_attribute("data-src-template") or 
                              img_el.get_attribute("data-src") or 
                              img_el.get_attribute("src"))
                except:
                    img_url = None

                if len(article_content) > 2:   # Only keep substantial articles
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "image": img_url,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except Exception as e:
                print(f"Error processing {link}: {e}")
                continue
    finally:
        driver.quit()
    return articles


# ================== Main ==================
targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/"
}

data_file = "data.json"

# Load existing data
if os.path.exists(data_file):
    with open(data_file, "r", encoding='utf-8') as f:
        full_db = json.load(f)
else:
    full_db = []

existing_urls = {a['url'] for a in full_db}

for cat, url in targets.items():
    print(f"Scraping {cat} from {url}...")
    new_arts = scrape_section(url, cat)
    
    for art in new_arts:
        if art['url'] not in existing_urls:
            full_db.insert(0, art)   # Newest first
            existing_urls.add(art['url'])

# Keep only latest 500 articles
full_db = full_db[:500]

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db, f, ensure_ascii=False, indent=4)

print(f"Total articles saved: {len(full_db)}")
