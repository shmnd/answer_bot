from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPEN_AI_API_KEY)

def extract_keyword_from_question(question_text):
    prompt = f"""
        Extract the most important medical keywords from the following clinical MCQ or query. Only return a comma-separated list of keywords — no explanation.
        Question:
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
        return keyword_response.replace(","," ")
    except Exception:
        return question_text # fallback to original if GPT fails