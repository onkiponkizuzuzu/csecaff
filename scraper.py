import os
import json
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
    
    # Additional stealth
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Stealth: hide webdriver flag
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # CDP: Block common trackers/paywall scripts
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*tinypass.com*", "*piano.io*", "*googletagservices.com*",
            "*cxense.com*", "*doubleclick.net*", "*adsystem*"
        ]
    })
    
    driver.set_page_load_timeout(120)
    return driver

def scrape_section(url, category, max_articles=12):
    driver = get_driver()
    articles = []
    try:
        print(f"Fetching list page: {url}")
        driver.get(url)
        time.sleep(7 + random.uniform(1, 3))  # Human-like delay

        # Extract unique article links (improve selector if site changes)
        elements = driver.find_elements(By.CSS_SELECTOR, "h3.title a, article h2 a, .story-card a")
        links = []
        for el in elements:
            href = el.get_attribute("href")
            if href and "/article" in href and href not in links:
                links.append(href)

        print(f"Found {len(links)} potential articles for {category}")

        for link in links[:max_articles]:
            try:
                print(f"  Scraping: {link}")
                driver.get(link)
                time.sleep(6 + random.uniform(1, 4))

                # Robust title extraction
                try:
                    title = driver.find_element(By.CSS_SELECTOR, "h1.title, h1.entry-title, [itemprop='headline']").text.strip()
                except NoSuchElementException:
                    title = driver.title.split(" | ")[0].strip()

                # Article body - improved selector fallback
                body_container = None
                selectors = [
                    'div.schemaDiv[itemprop="articleBody"]',
                    'div.article-body', 
                    'article[itemprop="articleBody"]',
                    '.content-body'
                ]
                for sel in selectors:
                    try:
                        body_container = driver.find_element(By.CSS_SELECTOR, sel)
                        break
                    except:
                        continue

                if not body_container:
                    continue

                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    if not text or len(text) < 20:
                        continue
                    if any(skip in text.lower() for skip in ["related stories", "photo credit", "also read", "subscribe"]):
                        continue
                    
                    item_type = "heading" if el.tag_name in ["h2", "h3", "h4"] else "text"
                    article_content.append({"type": item_type, "value": text})

                # Image with multiple fallbacks
                img_url = None
                try:
                    img_selectors = [
                        'div.article-picture img',
                        'img[itemprop="image"]',
                        '.lead-image img',
                        'figure img'
                    ]
                    for sel in img_selectors:
                        img_el = driver.find_element(By.CSS_SELECTOR, sel)
                        img_url = (img_el.get_attribute("data-src-template") or 
                                  img_el.get_attribute("data-src") or 
                                  img_el.get_attribute("src"))
                        if img_url and img_url.startswith("http"):
                            break
                except:
                    pass

                if len(article_content) >= 3:  # Minimum content quality
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "image": img_url,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "scraped_at": datetime.utcnow().isoformat()
                    })
                    print(f"    ✓ Saved: {title[:80]}...")

            except (TimeoutException, NoSuchElementException, WebDriverException) as e:
                print(f"    ✗ Failed: {str(e)[:100]}")
                continue
            except Exception as e:
                print(f"    Unexpected error: {e}")
                continue

    finally:
        driver.quit()
    
    return articles

# ==================== Main ====================

targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/",
    # Add more sections easily if needed
}

data_file = "data.json"

# Load existing data (with fallback)
if os.path.exists(data_file):
    with open(data_file, "r", encoding='utf-8') as f:
        full_db = json.load(f)
else:
    full_db = []

existing_urls = {a['url'] for a in full_db}

new_count = 0
for cat, url in targets.items():
    print(f"\n=== Scraping {cat} ===")
    new_arts = scrape_section(url, cat)
    
    for art in new_arts:
        if art['url'] not in existing_urls:
            full_db.insert(0, art)   # Newest first
            existing_urls.add(art['url'])
            new_count += 1

# Keep only latest 600 articles (increased limit)
full_db = full_db[:600]

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db, f, ensure_ascii=False, indent=2)

print(f"\n✅ Scrape complete. Added {new_count} new articles. Total: {len(full_db)}")
