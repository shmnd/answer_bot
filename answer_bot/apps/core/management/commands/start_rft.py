import os
from django.core.management.base import BaseCommand
from django.conf import settings
from openai import OpenAI

class Command(BaseCommand):
    help = "Start reinforcement fine-tuning (RFT) job on OpenAI"

    def handle(self, *args, **options):
        client = OpenAI(api_key=settings.OPEN_AI_API_KEY)

        response = client.fine_tuning.jobs.create(
            training_file="file-J2FhdNZfQkdmZevnetTMUt",  # 👈 replace with your actual uploaded file ID
            model="gpt-4"
        )

        self.stdout.write(self.style.SUCCESS("🎯 Fine-tuning job started!"))
        self.stdout.write(f"📄 Job ID: {response.id}")
        self.stdout.write(f"📊 Status: {response.status}")
