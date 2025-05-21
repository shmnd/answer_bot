import json
from django.conf import settings
from openai import OpenAI
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.questions.models import ImprovedResponse, FlaggedQuestion



client = OpenAI(api_key=settings.OPEN_AI_API_KEY) 
@method_decorator(csrf_exempt, name='dispatch')
class QuestionPrompt(LoginRequiredMixin, View):
    template_name = "dashboard/qusetion_prompt.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        try:
            data = json.loads(request.body)
            question = data.get("question", "").strip()
            explanation = data.get("explanation", "").strip()

            if not question:
                return JsonResponse({"response": "Question cannot be empty."}, status=400)

            system_prompt = """
                You are a clinical MCQ assistant designed to help students prepare for NEET PG, FMGE, and UPSC CMS.

                Your role is to:
                - Improve MCQ clarity (correct grammar, duplicate options, expand acronyms)
                - Determine and explain the correct answer
                - Provide deep clinical reasoning
                - Include a 'Review Synopsis' for every question like the Pearls & Treasures format
                - Use any provided explanation or uploaded document to enhance your answers

                ---

                **Final Question (Improved)**  
                <Rewrite the question clearly and clinically. If image-based, reference the image here. Expand all acronyms.>

                **All Options (Improved)**  
                A. <Option A (clear, relevant, non-redundant)>  
                B. <Option B>  
                C. <Option C>  
                D. <Option D>

                **Correct Answer**  
                <Correct answer letter>. <Full answer text>

                **Detailed Explanation**  

                - ✅ Explanation of the Correct Answer  
                    - <Step-by-step reasoning with clinical guidelines or textbook logic>

                - ❌ Explanation of Incorrect Options  
                    A. <Why A is wrong>  
                    B. <Why B is wrong>  
                    C. <Why C is wrong>  
                    D. <Why D is wrong>

                - 🔍 If explanation or write-up is provided: incorporate it into your explanation to avoid redundancy

                - 📷 If image is provided: explain what is shown and how it supports the answer

                ---

                **Review Synopsis: High-Yield Points on <Topic>**

                - <Subsection 1 (e.g., Etiology)>  
                    - <Bullet point 1>  
                    - <Bullet point 2>  

                - <Subsection 2 (e.g., Clinical Features)>  
                    - <Point 1>  
                    - <Point 2>  

                - <Subsection 3 (e.g., Treatment / Diagnosis)>  
                    - <Point 1>  
                    - <Point 2>

                *End with*: Would you like a follow-up question on this topic?

                Do not answer anything outside of the above format.
                """

            # Proper message list including system role
            messages = [{"role": "system", "content": system_prompt}]
            # Build ChatGPT messages
            messages.append({"role": "user", "content": question})

            if explanation:
                messages.append({
                    "role": "user",
                    "content": f"This explanation is provided as reference for improving the MCQ:\n\n{explanation}"
                })

            response = client.chat.completions.create(
                model = "gpt-4",
                messages=messages,
            )
            # Accessing the response content using dot notation
            response_text = response.choices[0].message.content


            # ''''''''''''''''''''''''''''''''''''''FOR RFT''''''''''''''''''''''''''''''''''''''''

            # all_completions = [choice.message.content for choice in response.choices]

            # # Save all for scoring later (RFT)
            # rft_data = {
            #     "prompt": {
            #         "messages": [{"role": "user", "content": question}]
            #     },
            #     "completions": [
            #         {"message": {"role": "assistant", "content": c}, "score": 0.0}
            #         for c in all_completions
            #     ]
            # }

            # # Save to file or DB table if you're batch processing
            # # rft_json_path = os.path.join(settings.BASE_DIR, "rft_dataset.jsonl")

            # # rft_training_json_path = os.path.join(settings.MEDIA_ROOT, "rft_training_dataset.json") #to give directly to covnert to json1
            # rft_json_path = os.path.join(settings.MEDIA_ROOT, "rft_dataset.jsonl")

            # with open(rft_json_path, "a", encoding="utf-8") as f1:
            #     # with open(rft_training_json_path, "a", encoding="utf-8") as f2:

            #     f1.write(json.dumps(rft_data) + "\n")
            #         # f2.write(json.dumps(rft_data) + "\n")


            # ''''''''''''''''''''''''''''''''''''''FOR RFT''''''''''''''''''''''''''''''''''''''''

            # Save both original and edited if provided
            Questions.objects.create(
                question=question,
                gpt_answer=response_text,
                user = request.user
            )

            return JsonResponse({"response": response_text})
        except Exception as e:
            return JsonResponse({"response": f"Error: {str(e)}"})
        


def process_bulk_question(question_text):
    normalized = question_text.strip().lower()

    # Find similar question
    existing_q = Questions.objects.filter(question__icontains=normalized).first()
    print(existing_q,'heloooooooooooooooooooooooooooooo')

    if not existing_q:
        FlaggedQuestion.objects.create(
            question=question_text,
            reason="Not found in DB"
        )
        return

    # Check if answer exists and matches
    if not existing_q.correct_answer:
        FlaggedQuestion.objects.create(
            question=question_text,
            reason="Missing answer",
            original=existing_q
        )
        return

    # Build prompt
    system_prompt = """
        You are a clinical MCQ assistant.

        Task: Compare old and new GPT-generated explanations for the same MCQ.
        - Decide which is better.
        - If both have strengths, combine them.
        - Return: improved explanation in clinical format.

        Format:
        **Question:** <rewrite improved>
        **Answer:** <correct answer>
        **Improved Explanation:**
        - ✅ <why correct is correct>
        - ❌ <why others are wrong>
        - 🧠 Review Summary
        """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Question: {question_text}"},
        {"role": "user", "content": f"Old Explanation:\n{existing_q.gpt_answer}"}
    ]

    # Call GPT
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )

    new_response = response.choices[0].message.content

    # Save to DB
    existing_q.old_gpt_answer = existing_q.gpt_answer
    existing_q.gpt_answer = new_response
    existing_q.save()



def read_and_process_file(file):
    import fitz  # For PDF
    from docx import Document

    name = file.name
    ext = name.split('.')[-1].lower()

    content = ""
    if ext == "txt":
        content = file.read().decode("utf-8")
    elif ext == "pdf":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        content = "\n".join([p.get_text() for p in doc])
    elif ext == "docx":
        doc = Document(file)
        content = "\n".join([p.text for p in doc.paragraphs])
    else:
        raise ValueError("Unsupported file type.")

    questions = [q.strip() for q in content.split("\n") if q.strip()]
    for q in questions:
        process_bulk_question(q)


def upload_bulk_questions(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        read_and_process_file(file)
        return JsonResponse({"status": "processed"})
