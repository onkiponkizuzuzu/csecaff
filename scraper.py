def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
   
    # Auto-detect Chrome binary (no hardcoded path needed)
    service = Service("/usr/bin/chromedriver")   # GitHub runner usually places it here after Chrome install
   
    driver = webdriver.Chrome(service=service, options=chrome_options)
   
    # --- CDP NETWORK BLOCKER (Piano / TinyPass paywall) ---
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*tinypass.com*", "*piano.io*", "*googletagservices.com*", "*cxense.com*"]
    })
   
    driver.set_page_load_timeout(180)
    return driver
