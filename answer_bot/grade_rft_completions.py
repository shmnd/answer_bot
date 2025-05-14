import os
import django
import json
from django.conf import settings
from openai import OpenAI

# 👇 Setup Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'answer_bot_core.settings')  # adjust if your settings module name is different
django.setup()

from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPEN_AI_API_KEY) 

# INPUT_PATH = os.path.join(settings.BASE_DIR, 'media', 'rft_dataset.jsonl')
# OUTPUT_PATH = os.path.join(settings.BASE_DIR, 'media', 'rft_scored.jsonl')
INPUT_PATH = os.path.join(settings.MEDIA_ROOT, 'rft_dataset.jsonl')
OUTPUT_PATH = os.path.join(settings.MEDIA_ROOT, 'rft_scored.jsonl')

grading_instructions = """
You are a clinical MCQ evaluator. Given a question and multiple assistant responses, assign a score between 0 and 1 to each completion.

Scoring Criteria:
- ✅ 1.0 = Completely correct answer + reasoning
- ✅ 0.8 = Correct answer, minor gaps
- ⚠️ 0.5 = Partially correct or vague
- ❌ 0.0 = Incorrect or irrelevant

Return ONLY a JSON list of scores like: [1.0, 0.8, 0.0]
"""

def grade_one_item(item):
    user_prompt = item["prompt"]["messages"][0]["content"]
    completions = [comp["message"]["content"] for comp in item["completions"]]

    grading_input = f"""Question:
{user_prompt}

Completions:
1. {completions[0]}

2. {completions[1]}

3. {completions[2]}

{grading_instructions}
"""

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are an expert clinical MCQ grader."},
            {"role": "user", "content": grading_input}
        ],
        temperature=0.3
    )

    score_line = response.choices[0].message.content.strip()

    try:
        scores = json.loads(score_line)
        return scores
    except Exception as e:
        print(f"❌ Failed to parse GPT score: {score_line} — {e}")
        return [0.0, 0.0, 0.0]  # fallback

with open(INPUT_PATH, 'r', encoding='utf-8') as infile, open(OUTPUT_PATH, 'w', encoding='utf-8') as outfile:
    for line in infile:
        try:
            item = json.loads(line)
            scores = grade_one_item(item)

            for i in range(len(scores)):
                item["completions"][i]["score"] = scores[i]

            outfile.write(json.dumps(item, ensure_ascii=False) + "\n")
            print(f"✅ Graded: {item['prompt']['messages'][0]['content'][:60]}... -> {scores}")
        except Exception as e:
            print(f"❌ Skipped due to error: {e}")
