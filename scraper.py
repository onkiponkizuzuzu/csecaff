import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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

def scrape_missing_ie_sections(base_url, category, existing_urls):
    driver = get_driver()
    articles = []
    all_links = []
    page = 1
    
    try:
        # Navigate standard pagination until we hit 60 links
        while len(all_links) < 60 and page <= 15:
            current_url = f"{base_url}page/{page}/" if page > 1 else base_url
            print(f"[{category}] Scanning page {page}...")
            driver.get(current_url)
            time.sleep(5)
            
            # IE section pages use different heading classes for their articles
            elements = driver.find_elements(By.CSS_SELECTOR, ".articles h2 a, h3.title a, .title a, .img-context h2 a, .img-context h3 a")
            current_links = []
            for el in elements:
                href = el.get_attribute("href")
                if href and "/article/explained/" in href and href not in all_links:
                    current_links.append(href)
            
            if not current_links:
                print(f"[{category}] No more valid links found on page {page}.")
                break
                
            all_links.extend(current_links)
            page += 1

        # Remove duplicates, filter out existing, and enforce strict 60 limit
        new_links = [link for link in list(set(all_links)) if link not in existing_urls]
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
    "Everyday Explainer": "https://indianexpress.com/section/explained/everyday-explainers/",
    "Law and Policy": "https://indianexpress.com/section/explained/explained-law/"
}

data_file = "data.json"
full_db = json.load(open(data_file, "r", encoding='utf-8')) if os.path.exists(data_file) else []
existing_urls = set(a['url'] for a in full_db)

for cat, url in missing_targets.items():
    print(f"Starting isolated scrape for missing category: {cat}")
    new_arts = scrape_missing_ie_sections(url, cat, existing_urls)
    
    for art in new_arts:
        full_db.insert(0, art)
        existing_urls.add(art['url'])

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:6000], f, ensure_ascii=False, indent=4) 

print(f"\nTemporary scrape completed. Total articles in database: {len(full_db)}")
