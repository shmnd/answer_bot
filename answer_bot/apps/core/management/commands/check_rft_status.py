import os
import django
from django.core.management.base import BaseCommand
from openai import OpenAI
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'answer_bot_core.settings')  # change if needed
django.setup()

client = OpenAI(api_key=settings.OPEN_AI_API_KEY)

class Command(BaseCommand):
    help = "Check status of the latest Reinforcement Fine-Tuning job"

    def handle(self, *args, **kwargs):
        try:
            jobs = client.fine_tuning.jobs.list(limit=1)
            if not jobs.data:
                self.stdout.write(self.style.WARNING("No RFT jobs found."))
                return

            job = jobs.data[0]
            job_id = job.id
            status = job.status
            model_name = job.fine_tuned_model
            error = job.error

            self.stdout.write("📄 Job ID: " + job_id)
            self.stdout.write("📊 Status: " + status)
            if model_name:
                self.stdout.write("✅ Fine-tuned Model ID: " + model_name)
            if error:
                self.stdout.write(self.style.ERROR(f"❌ Error: {error}"))
            elif status == "succeeded":
                self.stdout.write(self.style.SUCCESS("🎉 RFT completed! Your model is ready."))
            else:
                self.stdout.write("⏳ Still in progress...")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
