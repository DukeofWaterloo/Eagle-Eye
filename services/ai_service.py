import requests
import json
import logging
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_ai_response(review_text, business_type, tone="professional"):
    prompt = f"""
    As a {business_type} business owner, generate 3 response options to this customer review. 
    Use a {tone} tone. Review: "{review_text}"
    
    Format strictly as JSON: {{"options": ["response1", "response2", "response3"]}}
    """
    
    logger.info(f"Starting AI response generation for {business_type} business with {tone} tone")
    logger.info(f"Review text: {review_text}")
    logger.info(f"Ollama URL: {Config.OLLAMA_URL}")
    logger.info(f"AI Model: {Config.AI_MODEL}")
    
    try:
        request_data = {
            "model": Config.AI_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_gpu": 50  # Use 50% of GPU
            }
        }
        
        logger.info(f"Sending request to Ollama: {request_data}")
        
        response = requests.post(
            f"{Config.OLLAMA_URL}/api/generate",
            json=request_data,
            timeout=30  # 30 second timeout
        )
        
        logger.info(f"Ollama response status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"Ollama response data: {response_data}")
            
            if "response" in response_data:
                try:
                    parsed_response = json.loads(response_data["response"])
                    logger.info(f"Parsed response: {parsed_response}")
                    
                    if "options" in parsed_response and isinstance(parsed_response["options"], list):
                        logger.info(f"Successfully generated {len(parsed_response['options'])} responses")
                        return parsed_response["options"]
                    else:
                        logger.error("Response missing 'options' key or not a list")
                        raise Exception("Invalid response format")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Raw response: {response_data['response']}")
                    raise Exception(f"JSON parsing error: {e}")
            else:
                logger.error("Response missing 'response' key")
                logger.error(f"Full response: {response_data}")
                raise Exception("Response missing 'response' key")
        else:
            logger.error(f"AI service returned status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            raise Exception(f"AI service error: {response.status_code}")
            
    except requests.exceptions.Timeout:
        logger.error("AI service request timed out after 30 seconds")
        fallback_responses = [
            "Thank you for your feedback! We're currently experiencing high demand.",
            "We appreciate your review and will respond shortly.",
            "Thank you for taking the time to share your experience with us."
        ]
        logger.info(f"Returning fallback responses: {fallback_responses}")
        return fallback_responses
        
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to AI service")
        fallback_responses = [
            "Thank you for your feedback!",
            "We appreciate you taking the time to review us.",
            "We'll address your concerns immediately."
        ]
        logger.info(f"Returning fallback responses: {fallback_responses}")
        return fallback_responses
        
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        fallback_responses = [
            "Thank you for your feedback!",
            "We appreciate you taking the time to review us.",
            "We'll address your concerns immediately."
        ]
        logger.info(f"Returning fallback responses: {fallback_responses}")
        return fallback_responses
