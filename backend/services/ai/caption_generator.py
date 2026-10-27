import os
from google import genai
from backend.config import settings
import logging
import json

logger = logging.getLogger(__name__)

async def generate_caption(topic: str) -> dict:
    # Αν δεν υπάρχει API key, επιστρέφουμε ένα default κείμενο (ώστε να μην σκάει η εφαρμογή)
    if not settings.gemini_api_key:
        return {
            "caption": "Το AI είναι ανενεργό (λείπει το API Key).", 
            "hashtags": "[]"
        }
    
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        
        prompt = f"""
        Είσαι ένας Social Media Manager. Γράψε ένα ελκυστικό caption (περιγραφή) για ένα κάθετο βίντεο (TikTok/Shorts/Reels).
        Το θέμα του βίντεο είναι: "{topic}"
        
        Απάντησε ΑΥΣΤΗΡΑ ΜΟΝΟ με ένα JSON object αυτής της μορφής (χωρίς markdown, μόνο το JSON):
        {{
            "caption": "Το κείμενο εδώ, φιλικό, με emojis, και ένα ερώτημα στο τέλος...",
            "hashtags": ["#tag1", "#tag2", "#tag3"]
        }}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        
        return {
            "caption": data.get("caption", ""),
            "hashtags": json.dumps(data.get("hashtags", []))
        }
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return {"caption": "Σφάλμα κατά τη δημιουργία caption.", "hashtags": "[]"}