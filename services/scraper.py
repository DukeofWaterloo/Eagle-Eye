import requests
from bs4 import BeautifulSoup
import re
from services.db_service import DBService
from services.ai_service import generate_ai_response
from services.alert_service import send_sms_alert
from config import Config

def scrape_google_reviews(business_name, place_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        reviews = []
        # Simplified selector - real implementation would be more robust
        review_elements = soup.select('.MyEned')
        
        for element in review_elements:
            text_element = element.select_one('.wiI7pd')
            text = text_element.text if text_element else ""
            
            # Extract rating from aria-label
            rating_element = element.select_one('.kvMYJc')
            rating_match = re.search(r'(\d+)', rating_element['aria-label']) if rating_element else None
            rating = int(rating_match.group(1)) if rating_match else 0
            
            if text and rating > 0:
                reviews.append({"text": text, "rating": rating})
        
        return reviews
    except Exception as e:
        print(f"Scraping error: {e}")
        return []
