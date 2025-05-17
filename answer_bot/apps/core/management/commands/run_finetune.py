import openai
from django.conf import settings

client = openai.OpenAI(api_key=settings.OPEN_AI_API_KEY)

response = client.fine_tuning.jobs.create(
    training_file="file-5sFiyjMt8ttsJKy8jCiUgM",
    model="gpt-4-1106-preview"
)

print(response)
