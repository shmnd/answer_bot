from openai import OpenAI
from django.conf import settings
import logging
logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPEN_AI_API_KEY)

def extract_keyword_from_question(question_text):
    prompt = f"""
        You are ChatGPT (OpenAI o3), acting purely as a *keyword-extraction engine* for multiple-choice questions.  
        When I give you an MCQ (stem, all options, the correct answer, and the explanation), you MUST return *only* a ranked, comma-separated list of keywords that can be passed directly to an Elasticsearch query.

        *Extraction & ranking rules*

        1. Scan the entire input—question stem, *every* option (correct + incorrect), and the explanation.  
        2. Pull out all clinically or conceptually important terms and short phrases (2–4 words max each).  
        3. Place the most diagnostic / discriminating term first, then list successively less-important terms.  
        4. Make sure the list covers the correct answer *and* every incorrect option (each distractor must contribute ≥ 1 keyword).  
        5. Remove stop-words, punctuation, and duplicates. Do *not* add commentary, numbering, or line breaks.

        *Output format*

        One plain line, keywords separated only by commas.

        Example (for illustration only—not part of the prompt output)  
        Input MCQ about aortic dissection →  
        Output:  
        aortic dissection, tearing chest pain, hypertension, diastolic murmur, aortic regurgitation, acute pericarditis, positional chest pain, diffuse ST elevation, myocardial infarction, crushing chest pain, regional ECG changes, pulmonary embolism, pleuritic chest pain, dyspnea
        \"\"\"{question_text}\"\"\"
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a medical keyword extractor."},
                {"role": "user", "content": prompt}
            ]
        )
        keyword_response = response.choices[0].message.content.strip()
        return [kw.strip() for kw in keyword_response.split(",") if kw.strip()]
    
    except Exception as e:
        logger.exception(f"{e}--OpenAI keyword extraction failed.")
        # fallback: basic keyword splitting
        return [kw.strip() for kw in question_text.split() if len(kw) > 3]