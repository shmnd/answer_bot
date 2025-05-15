import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Fix RFT file format: remove prompt wrapper and rename score → reward"

    def handle(self, *args, **kwargs):
        input_path = os.path.join(settings.MEDIA_ROOT, "rft_scored.jsonl")
        output_path = os.path.join(settings.MEDIA_ROOT, "rft_scored_fixed.jsonl")

        if not os.path.exists(input_path):
            self.stdout.write(self.style.ERROR("❌ File not found: rft_scored.jsonl"))
            return

        fixed_count = 0

        with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
            for line in infile:
                try:
                    item = json.loads(line)

                    # Move messages from prompt → top-level
                    if "prompt" in item and "messages" in item["prompt"]:
                        item["messages"] = item["prompt"]["messages"]
                        del item["prompt"]

                    # Rename score → reward
                    for comp in item.get("completions", []):
                        if "score" in comp:
                            comp["reward"] = comp["score"]
                            del comp["score"]

                    outfile.write(json.dumps(item, ensure_ascii=False) + "\n")
                    fixed_count += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠️ Skipping invalid line: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed_count} examples. Output: rft_scored_fixed.jsonl"))
