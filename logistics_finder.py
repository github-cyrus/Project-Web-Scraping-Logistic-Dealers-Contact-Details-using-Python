import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re
from urllib.parse import urljoin, urlparse
import json
from WebScrap import LogisticsContractorScraper

class LogisticsFinder:
    def __init__(self):
        """Initialize the logistics finder"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.setup_driver()
        self.logistics_companies = []
        
        # List of known logistics companies
        self.known_companies = [
            "https://www.allcargologistics.com/",
            "https://capricornlogistics.com/",
            "https://www.dhl.com/in-en/home.html",
            "https://www.maersk.com/",
            "https://www.fedex.com/en-in/home.html",
            "https://www.ups.com/in/en/Home.page",
            "https://www.bluedart.com/",
            "https://www.gati.com/",
            "https://www.safexpress.com/",
            "https://www.tciexpress.in/",
            "https://www.dtdc.in/",
            "https://www.xpressbees.com/",
            "https://www.delhivery.com/",
            "https://www.ecomexpress.in/",
            "https://www.shadowfax.in/"
        ]
        
        # Search queries for finding more companies
        self.search_queries = [
            "top logistics companies in India",
            "freight forwarding companies India",
            "shipping and logistics companies India",
            "supply chain companies India",
            "cargo services India",
            "transportation logistics India"
        ]

    def setup_driver(self):
        """Configure Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(f'--user-agent={self.headers["User-Agent"]}')
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        # Set window size
        self.driver.set_window_size(1920, 1080)
        
        # Mask automation
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = {
                    runtime: {}
                };
            '''
        })

    def search_google(self, query):
        """Search Google for logistics companies"""
        try:
            search_url = f"https://www.google.com/search?q={query}"
            self.driver.get(search_url)
            time.sleep(random.uniform(2, 4))
            
            # Extract all result links
            links = self.driver.find_elements(By.CSS_SELECTOR, 'div.g a')
            urls = []
            
            for link in links:
                try:
                    url = link.get_attribute('href')
                    if url and url.startswith('http') and not any(x in url.lower() for x in ['google', 'youtube', 'facebook', 'linkedin']):
                        urls.append(url)
                except:
                    continue
            
            return urls
        except Exception as e:
            print(f"Error searching Google: {str(e)}")
            return []

    def find_logistics_companies(self):
        """Find logistics companies through various methods"""
        all_urls = set(self.known_companies)
        
        # Search Google for more companies
        for query in self.search_queries:
            print(f"Searching for: {query}")
            urls = self.search_google(query)
            all_urls.update(urls)
            time.sleep(random.uniform(10, 15))  # Be nice to Google
        
        return list(all_urls)

    def scrape_companies(self):
        """Scrape information from found companies"""
        urls = self.find_logistics_companies()
        print(f"Found {len(urls)} potential logistics companies")
        
        all_data = []
        for url in urls:
            try:
                print(f"\nProcessing: {url}")
                # Try to find contact page
                contact_url = url
                if not url.lower().endswith('contact'):
                    parsed_url = urlparse(url)
                    contact_url = urljoin(url, 'contact')
                
                # Create a scraper instance for this company
                scraper = LogisticsContractorScraper(contact_url)
                company_data = scraper.scrape_data()
                
                if company_data:
                    all_data.extend(company_data)
                    print(f"Successfully scraped data from {url}")
                
                time.sleep(random.uniform(5, 10))  # Be nice to the servers
                
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                continue
        
        return all_data

    def save_results(self, data, filename='all_logistics_companies.csv'):
        """Save scraped data to CSV"""
        if not data:
            print("No data to save")
            return
        
        # Convert to DataFrame for easier handling
        df = pd.DataFrame(data)
        
        # Save to CSV
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
        
        # Print summary
        print("\nSummary of collected data:")
        print(f"Total companies found: {len(data)}")
        print(f"Companies with email: {df['emails'].notna().sum()}")
        print(f"Companies with phone: {df['phone_numbers'].notna().sum()}")
        print(f"Companies with website: {df['website'].notna().sum()}")
        
        if 'city' in df.columns:
            print("\nTop cities:")
            print(df['city'].value_counts().head())

def main():
    finder = LogisticsFinder()
    print("Starting logistics company search...")
    
    # Scrape company data
    data = finder.scrape_companies()
    
    # Save results
    finder.save_results(data)

if __name__ == "__main__":
    main()
