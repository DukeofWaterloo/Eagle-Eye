import os
from celery import Celery
from services.db_service import DBService
from services.scraper import scrape_google_reviews
from services.ai_service import generate_ai_response
from services.alert_service import send_sms_alert, send_email_alert
from config import Config
import logging
import time
from celery.schedules import crontab

celery = Celery('celery_worker', broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'))

db_service = DBService()

@celery.task
def process_reviews():
    logging.info("Starting review processing task...")
    try:
        # Get all businesses
        with db_service.conn.cursor() as cur:
            cur.execute("SELECT id, name, gmb_account_id, owner_phone, response_tone, owner_email FROM businesses")
            businesses = cur.fetchall()
        for biz in businesses:
            biz_id, name, gmb_id, phone, tone, email = biz
            reviews = scrape_google_reviews(name, gmb_id)
            for review in reviews:
                # Check if review exists
                with db_service.conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM reviews WHERE review_text = %s AND business_id = %s",
                        (review["text"], biz_id)
                    )
                    if cur.fetchone():
                        continue
                # Save new review
                review_id = db_service.save_review(biz_id, review["text"], review["rating"])
                # Generate AI responses
                responses = generate_ai_response(review["text"], "restaurant", tone)
                db_service.save_ai_responses(review_id, responses)
                # Send SMS alert
                if phone:
                    preview = f"{review['rating']} stars: {review['text']}"
                    send_sms_alert(phone, preview, name)
                # Send email alert
                if email:
                    preview = f"{review['rating']} stars: {review['text']}"
                    send_email_alert(email, preview, name)
    except Exception as e:
        logging.error(f"Error in review processing task: {e}")

# Celery Beat schedule
celery.conf.beat_schedule = {
    'process-reviews-every-interval': {
        'task': 'celery_worker.process_reviews',
        'schedule': int(os.environ.get('SCRAPE_INTERVAL', 300)),  # seconds
    },
}
celery.conf.timezone = 'UTC' 