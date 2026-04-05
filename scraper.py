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

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
    
    chrome_options.binary_location = "/usr/bin/google-chrome"
    service = Service("/usr/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*",
            "*evolok*", "*ev-engagement*", "*paywall*", "*premium*", "*subscription*"
        ]
    })
    
    driver.set_page_load_timeout(180)
    return driver

def scrape_missing_ie_load_more(url, category, existing_urls):
    driver = get_driver()
    articles = []
    all_links = []
    
    try:
        driver.get(url)
        time.sleep(5)

        clicks = 0
        max_clicks = 40  # Allow enough clicks to find 60 new articles

        while clicks < max_clicks:
            elements = driver.find_elements(By.CSS_SELECTOR, "#tag_article .details h3 a")
            current_links = list(set([el.get_attribute("href") for el in elements if "/article/explained/" in el.get_attribute("href")]))
            all_links = list(set(all_links + current_links))
            
            # Check how many NEW links we have found so far
            new_links = [link for link in all_links if link not in existing_urls]

            if len(new_links) >= 60:
                print(f"[{category}] Found {len(new_links)} new links. Stopping clicks.")
                break

            try:
                load_more = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "load_tag_article"))
                )
                driver.execute_script("arguments[0].click();", load_more)
                clicks += 1
                print(f"[{category}] Clicked Load More {clicks} (Found {len(new_links)} new articles so far)")
                time.sleep(3)
            except:
                print(f"[{category}] Reached end of available articles.")
                break 

        # Enforce strict 60 limit
        new_links = new_links[:60]
        print(f"[{category}] Proceeding to extract {len(new_links)} new articles...")

        for link in new_links:
            try:
                driver.get(link)
                time.sleep(5)

                driver.execute_script("""
                    document.querySelectorAll('ev-engagement, .ev-engagement, .content-login-wrapper, .ev-paywall-template').forEach(el => el.remove());
                    document.querySelectorAll('.ev-meter-content, .ie-premium-content-block, [class*="paywall"], [id*="paywall"]').forEach(el => {
                        el.style.display = 'block';
                        el.style.height = 'auto';
                        el.style.overflow = 'visible';
                        el.style.maskImage = 'none';
                        el.style.webkitMaskImage = 'none';
                    });
                    const content = document.getElementById('pcl-full-content');
                    if (content) {
                        content.style.display = 'block';
                        content.style.height = 'auto';
                        content.style.overflow = 'visible';
                    }
                """)

                body_container = driver.find_element(By.ID, "pcl-full-content")
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h2, h3, h4")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    if not text or any(skip in text for skip in ["Subscriber Only", "Story continues below", "ALSO READ", "Subscribe"]):
                        continue
                    
                    article_content.append({
                        "type": "heading" if el.tag_name in ["h2", "h3", "h4"] else "text",
                        "value": el.get_attribute('innerHTML').strip()
                    })

                title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                if len(article_content) > 3:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
                    print(f"[{category}] Successfully extracted: {title}")
            except Exception as e:
                print(f"[{category}] Failed to extract link: {link}")
                continue
                
    finally:
        driver.quit()
        
    return articles

# ================== Execution ==================
missing_targets = {
    "Global": "https://indianexpress.com/about/explained-global/?ref=explained_pg",
    "Sci-Tech": "https://indianexpress.com/about/explained-sci-tech/",
    "Economics": "https://indianexpress.com/about/explained-economics/?ref=explained_pg",
    "Expert Explains": "https://indianexpress.com/about/an-expert-explains/?ref=explained_pg"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
existing_urls = set(a['url'] for a in full_db)

for cat, url in missing_targets.items():
    print(f"\nStarting isolated scrape for category: {cat}")
    new_arts = scrape_missing_ie_load_more(url, cat, existing_urls)
    
    for art in new_arts:
        full_db.insert(0, art)
        existing_urls.add(art['url'])

with open(data_file, "w", encoding='utf-8') as f:
    # Cap safely increased to handle the new batches
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4) 

print(f"\nTemporary scrape completed. Total articles in database: {len(full_db)}")
