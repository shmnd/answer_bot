from django.core.management.base import BaseCommand
from apps.questions.models import ImprovedResponse
from answer_bot_core.helpers.elastic_client import es

class Command(BaseCommand):
    help = "Reindex all ImprovedResponse MCQs into Elasticsearch"

    def handle(self, *args, **options):
        count = 0
        total = ImprovedResponse.objects.count()

        self.stdout.write(f"\nIndexing {total} MCQs to Elasticsearch...\n")

        for obj in ImprovedResponse.objects.all():
            es.index(index="mcq_questions", id=obj.id, body={
                "question": obj.question,
                "opa": obj.opa,
                "opb": obj.opb,
                "opc": obj.opc,
                "opd": obj.opd,
                "correct_answer": obj.correct_answer,
                "explanation": obj.explanation
            })
            count += 1

        self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully indexed {count} MCQs into Elasticsearch."))