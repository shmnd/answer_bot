import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Convert MCQ-format JSON to RFT-compatible JSONL format'

    def handle(self, *args, **kwargs):
        input_path = os.path.join(settings.MEDIA_ROOT, 'input_compliance_data.json')
        output_path = os.path.join(settings.MEDIA_ROOT, 'train_data.jsonl')

        if not os.path.exists(input_path):
            self.stdout.write(self.style.ERROR(f"❌ File not found: {input_path}"))
            return

        try:
            with open(input_path, 'r', encoding='utf-8') as infile:
                data = json.load(infile)

            with open(output_path, 'w', encoding='utf-8') as outfile:
                count = 0
                for item in data:
                    try:
                        question_text = item.get("question", "").strip()
                        option_a = item.get("opa", "").strip()
                        option_b = item.get("opb", "").strip()
                        option_c = item.get("opc", "").strip()
                        option_d = item.get("opd", "").strip()
                        correct_option = item.get("cop", "").strip()
                        explanation = item.get("exp", "").strip()

                        # Build a compliant message
                        full_prompt = (
                            f"{question_text}\n\n"
                            f"A. {option_a}\n"
                            f"B. {option_b}\n"
                            f"C. {option_c}\n"
                            f"D. {option_d}\n\n"
                            f"Choose the correct option and explain why."
                        )

                        # RFT format
                        output_line = {
                            "messages": [
                                {"role": "user", "content": full_prompt}
                            ],
                            "compliant": correct_option,
                            "explanation": explanation
                        }

                        outfile.write(json.dumps(output_line, ensure_ascii=False) + "\n")
                        count += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"⚠️ Skipping item due to error: {e}"))

            self.stdout.write(self.style.SUCCESS(f"✅ Converted {count} questions to: {output_path}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
