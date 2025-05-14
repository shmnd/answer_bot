import os
import django
from django.conf import settings
from openai import OpenAI

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'answer_bot_core.settings')
django.setup()

# Init OpenAI client
client = OpenAI(api_key=settings.OPEN_AI_API_KEY)

# List fine-tuning jobs
response = client.fine_tuning.jobs.list()

print("\n📋 Listing Fine-Tuning Jobs:")
for job in response.data:
    print(job.id,'jobbbbbbbbbbbbbbbbbbbb')
    print(f"ID: {job.id}, Status: {job.status}, Model: {job.model}, Created: {job.created_at}")
