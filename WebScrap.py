import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import csv
import re
import random
from urllib.parse import urljoin, urlparse
import json

class LogisticsContractorScraper:
    def __init__(self, url):
        """Initialize the web scraper"""
        self.url = url
        self.base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        self.setup_driver()
        self.contractors = []

    def setup_driver(self):
        """Configure Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Add custom headers
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        from webdriver_manager.chrome import ChromeDriverManager
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

    def wait_and_find_element(self, by, value, timeout=10):
        """Wait for and find an element"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except Exception:
            return None

    def wait_and_find_elements(self, by, value, timeout=10):
        """Wait for and find multiple elements"""
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
            return elements
        except Exception:
            return []

    def safe_click(self, element):
        """Safely click an element using JavaScript"""
        try:
            self.driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False

    def random_sleep(self, min_sec=1, max_sec=3):
        """Add random delay"""
        time.sleep(random.uniform(min_sec, max_sec))

    def extract_text(self, element):
        """Safely extract text from an element"""
        try:
            return element.text.strip()
        except Exception:
            return ""

    def clean_html(self, text):
        """Clean HTML tags from text"""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', ' ', text)
        # Fix spaces
        clean = re.sub(r'\s+', ' ', clean)
        # Clean up special characters
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"')
        return clean.strip()

    def scrape_data(self):
        """Scrape contractor data"""
        try:
            print("Accessing website...")
            self.driver.get(self.url)
            self.random_sleep(3, 5)

            # Wait for page to load
            self.wait_and_find_element(By.TAG_NAME, 'body')
            
            # Extract data from the page
            print("Extracting data...")
            
            # For Capricorn Logistics, look for specific contact information
            contact_info = {}
            
            # Find the contact information section
            contact_sections = self.wait_and_find_elements(
                By.CSS_SELECTOR,
                '.contact-info, .contact-details, .contact-us, #contact'
            )
            
            # Process all text content
            all_text = ""
            for section in contact_sections:
                all_text += self.extract_text(section) + "\n"
            
            # Get specific elements
            address_elements = self.wait_and_find_elements(
                By.XPATH,
                "//*[contains(text(), 'Add') or contains(text(), 'Address')]"
            )
            
            for elem in address_elements:
                try:
                    parent = elem.find_element(By.XPATH, './..')
                    address_text = self.clean_html(parent.get_attribute('innerHTML'))
                    if 'Add' in address_text or 'Address' in address_text:
                        all_text += address_text + "\n"
                except:
                    continue
            
            # Get phone numbers specifically
            phone_elements = self.wait_and_find_elements(
                By.XPATH,
                "//a[contains(@href, 'tel:')]"
            )
            
            for elem in phone_elements:
                try:
                    phone = elem.get_attribute('href').replace('tel:', '').strip()
                    all_text += phone + "\n"
                except:
                    continue
            
            # Get email addresses specifically
            email_elements = self.wait_and_find_elements(
                By.XPATH,
                "//a[contains(@href, 'mailto:')]"
            )
            
            for elem in email_elements:
                try:
                    email = elem.get_attribute('href').replace('mailto:', '').strip()
                    all_text += email + "\n"
                except:
                    continue
            
            # Clean up the text
            all_text = self.clean_html(all_text)
            
            # Extract emails
            emails = self.extract_emails(all_text)
            if emails:
                contact_info['emails'] = emails
            
            # Extract phone numbers
            phones = self.extract_phone_numbers(all_text)
            if phones:
                contact_info['phone_numbers'] = phones
            
            # Extract location details
            location_info = self.extract_location_details(all_text)
            if location_info:
                # Clean up address
                if 'address' in location_info:
                    address = location_info['address']
                    # Remove common prefixes
                    address = re.sub(r'^.*?(?:Address|Add|Location)[:\s]*', '', address, flags=re.IGNORECASE)
                    # Clean up the address
                    address = re.sub(r'\s+', ' ', address).strip()
                    location_info['address'] = address
                contact_info.update(location_info)
            
            # Get company name
            contact_info['name'] = "Capricorn Logistics"
            contact_info['website'] = self.url
            
            # Try to find products/services
            services_sections = self.wait_and_find_elements(
                By.XPATH,
                '//*[contains(text(), "Services") or contains(text(), "Products")]'
            )
            
            products = []
            for section in services_sections:
                try:
                    parent = section.find_element(By.XPATH, './..')
                    items = parent.find_elements(By.TAG_NAME, 'li')
                    for item in items:
                        product = self.clean_html(item.get_attribute('innerHTML'))
                        if product and not any(p.lower() == product.lower() for p in products):
                            products.append(product)
                except:
                    continue
            
            if products:
                contact_info['products'] = products
            
            # Clean up empty values
            contact_info = {k: v for k, v in contact_info.items() if v}
            
            if contact_info:
                print(f"Found contractor: {contact_info.get('name', 'Unknown')}")
                self.contractors.append(contact_info)
            
            print(f"Found {len(self.contractors)} contractors")
            return self.contractors
            
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return []
        finally:
            self.driver.quit()

    def extract_emails(self, text):
        """Extract email addresses"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return list(set(re.findall(email_pattern, text)))

    def extract_phone_numbers(self, text):
        """Extract phone numbers"""
        patterns = [
            r'(?:\+91|0)?[-\s]?\d{10}',  # Indian mobile
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # XXX-XXX-XXXX
            r'\d{4}[-.\s]?\d{3}[-.\s]?\d{3}',  # XXXX-XXX-XXX
            r'\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'  # International
        ]
        
        phones = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phones.update(matches)
        
        # Clean up phone numbers
        cleaned_phones = set()
        for phone in phones:
            # Remove all non-digit characters
            digits = re.sub(r'\D', '', phone)
            # Add back the plus sign for international numbers
            if len(digits) > 10:
                cleaned_phones.add('+' + digits)
            else:
                cleaned_phones.add(digits)
        
        return list(cleaned_phones)

    def extract_location_details(self, text):
        """Extract location details"""
        location_info = {}
        
        # Extract address first
        address_pattern = r'(?i)(?:address|location)[:\s]*(.*?)(?:\n|$)'
        address_match = re.search(address_pattern, text)
        if address_match:
            location_info['address'] = address_match.group(1).strip()
        
        # Extract pincode
        pincode_match = re.search(r'\b\d{6}\b', text)
        if pincode_match:
            location_info['pincode'] = pincode_match.group()
        
        # Common Indian cities and states
        cities = ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 
                 'Pune', 'Ahmedabad', 'Surat', 'Jaipur', 'Lucknow', 'Kanpur']
        
        states = ['Maharashtra', 'Delhi', 'Karnataka', 'Telangana', 'Tamil Nadu', 
                 'West Bengal', 'Gujarat', 'Rajasthan', 'Uttar Pradesh', 'Kerala']
        
        # Find city and state
        for city in cities:
            if re.search(rf'\b{city}\b', text, re.IGNORECASE):
                location_info['city'] = city
                break
        
        for state in states:
            if re.search(rf'\b{state}\b', text, re.IGNORECASE):
                location_info['state'] = state
                break
        
        location_info['country'] = 'India'
        
        return location_info

    def save_to_csv(self, data, filename='logistics_contractors.csv'):
        """Save data to CSV"""
        if not data:
            print("No data to save")
            return
        
        # Flatten list fields
        flattened_data = []
        for item in data:
            flat_item = item.copy()
            for key, value in flat_item.items():
                if isinstance(value, list):
                    flat_item[key] = ', '.join(str(v) for v in value)
            flattened_data.append(flat_item)
        
        # Get all possible keys
        keys = set()
        for item in flattened_data:
            keys.update(item.keys())
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted(keys))
            writer.writeheader()
            writer.writerows(flattened_data)
        
        print(f"Data saved to {filename}")

    def generate_insights(self, data):
        """Generate insights from data"""
        insights = {
            'total_contractors': len(data),
            'contact_stats': {
                'with_email': sum(1 for item in data if item.get('emails')),
                'with_phone': sum(1 for item in data if item.get('phone_numbers')),
                'with_website': sum(1 for item in data if item.get('website'))
            },
            'locations': {
                'cities': {},
                'states': {}
            },
            'products': {}
        }
        
        for item in data:
            # Location statistics
            if 'city' in item:
                city = item['city']
                insights['locations']['cities'][city] = insights['locations']['cities'].get(city, 0) + 1
            
            if 'state' in item:
                state = item['state']
                insights['locations']['states'][state] = insights['locations']['states'].get(state, 0) + 1
            
            # Product statistics
            if 'products' in item:
                products = item['products'] if isinstance(item['products'], list) else [item['products']]
                for product in products:
                    insights['products'][product] = insights['products'].get(product, 0) + 1
        
        return insights

def main():
    url = "https://www.allcargologistics.com/"
    
    scraper = LogisticsContractorScraper(url)
    print("Starting data extraction...")
    
    data = scraper.scrape_data()
    scraper.save_to_csv(data)
    
    insights = scraper.generate_insights(data)
    print("\nInsights:")
    print(f"Total contractors: {insights['total_contractors']}")
    print(f"Contractors with email: {insights['contact_stats']['with_email']}")
    print(f"Contractors with phone: {insights['contact_stats']['with_phone']}")
    print(f"Contractors with website: {insights['contact_stats']['with_website']}")
    
    if insights['locations']['cities']:
        print("\nTop cities:")
        for city, count in sorted(insights['locations']['cities'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {city}: {count}")

if __name__ == "__main__":
    main()