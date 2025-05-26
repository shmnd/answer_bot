from apps.questions.models import ImprovedResponse
from answer_bot_core.helpers.elastic_client import es

def index_all_mcqs():
    for q in ImprovedResponse.objects.all():
        es.index(index="mcq_questions",id=q.id,body={
            "question": q.question,
            "options":[q.opa, q.opb, q.opc, q.opd],
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
        })



# from answer_bot_core.helpers.indexer import index_all_mcqs
# index_all_mcqs()
