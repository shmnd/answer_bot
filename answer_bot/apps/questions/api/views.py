from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from openai import OpenAI
from django.conf import settings
from apps.questions.models import ImprovedResponse
from .serializers import MCQSerializer
from answer_bot_core.helpers.response import ResponseInfo
from drf_yasg.utils import swagger_auto_schema

client = OpenAI(api_key=settings.OPEN_AI_API_KEY)

class ProcessMCQView(APIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(ProcessMCQView,self).__init__(**kwargs)

    serializer_class = MCQSerializer

    @swagger_auto_schema(request_body=MCQSerializer,tags=["Questions"])
    def post(self, request):
        try:
            data = request.data
            serializer = self.serializer_class(data=data, context={'request': request})
            
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format["status"] = False
                self.response_format["errors"] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)
            
            if not data:
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format["status"] = False
                self.response_format["errors"] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            # Step 1: Save original to DB
            instance = serializer.save()

            # Step 2: Prompt 1 — Get GPT's answer to question
            question = data['question']
            options = {
                "A": data['opa'],
                "B": data['opb'],
                "C": data['opc'],
                "D": data['opd'],
            }
            prompt_1 = f"""You are a medical exam assistant.

                Read the following MCQ and select the correct answer:

                Question: {question}

                A. {options['A']}
                B. {options['B']}
                C. {options['C']}
                D. {options['D']}

                Just give your answer in the format: 'Answer: <letter>' followed by an explanation."""

            try:
                response_1 = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Answer the medical MCQ with reasoning."},
                        {"role": "user", "content": prompt_1}
                    ]
                )
                gpt_response = response_1.choices[0].message.content.strip()

                # Extract answer letter
                import re
                match = re.search(r"(?i)answer[:\-]?\s*([A-D])", gpt_response)
                gpt_answer_letter = match.group(1).upper() if match else None

                instance.gpt_answer = gpt_answer_letter
                instance.gpt_explanation = gpt_response
                instance.save()

                if not gpt_answer_letter or gpt_answer_letter != data['correct_answer'].strip().upper():
                    return Response({
                        "status": "incorrect",
                        "message": "GPT answer does not match provided correct answer. Human verification needed.",
                        "gpt_answer": gpt_answer_letter,
                        "gpt_explanation": gpt_response
                    }, status=status.HTTP_200_OK)

                # Step 3: Prompt 2 — Improve question using both inputs
                prompt_2 = f"""You are a medical educator. Given the following MCQ with original explanation and GPT explanation, rewrite and improve the question and answer.

                    Original:
                    Question: {question}
                    A. {options['A']}
                    B. {options['B']}
                    C. {options['C']}
                    D. {options['D']}
                    Correct Answer: {data['correct_answer']}
                    Explanation: {data['explanation']}

                    GPT Explanation: {gpt_response}

                    Now return improved content in this format:

                    **Improved Question**: <...>
                    **Improved Options**:
                    A. ...
                    B. ...
                    C. ...
                    D. ...
                    **Correct Answer**: <letter>. <option text>
                    **Improved Explanation**:
                    - ✅ <why correct is correct>
                    - ❌ <why others are wrong>
                    - 🧠 Review Summary"""

                response_2 = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Improve and rewrite the MCQ using both explanations."},
                        {"role": "user", "content": prompt_2}
                    ]
                )
                improved_output = response_2.choices[0].message.content.strip()

                question_match = re.search(r"\*\*Improved Question\*\*:\s*(.+)", improved_output)
                instance.improved_question = question_match.group(1).strip() if question_match else None

                # Extract improved options A–D
                for option_key in ['A', 'B', 'C', 'D']:
                    pattern = rf"{option_key}\.\s*(.+)"
                    match = re.search(pattern, improved_output)
                    if match:
                        setattr(instance, f"improved_op{option_key.lower()}", match.group(1).strip())

                # Optionally: extract correct answer again
                correct_match = re.search(r"\*\*Correct Answer\*\*:\s*([A-D])\.\s*(.+)", improved_output)

                if correct_match:
                    instance.correct_answer = correct_match.group(1).strip()

                instance.improved_explanation = improved_output
                instance.is_verified = True
                instance.save()

                # return Response({
                #     "status": "success",
                #     "improved": improved_output
                # }, status=status.HTTP_200_OK)

                self.response_format['status_code'] = status.HTTP_201_CREATED
                self.response_format["message"] = "success"
                self.response_format["status"] = True
                self.response_format["data"] = improved_output
                return Response(self.response_format, status=status.HTTP_201_CREATED)

            except Exception as e:
                self.response_format['status_code'] = status.HTTP_500_INTERNAL_SERVER_ERROR
                self.response_format['status'] = False
                self.response_format['message'] = str(e)
                return Response(self.response_format, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            self.response_format['status_code'] = status.HTTP_500_INTERNAL_SERVER_ERROR
            self.response_format['status'] = False
            self.response_format['message'] = str(e)
            return Response(self.response_format, status=status.HTTP_500_INTERNAL_SERVER_ERROR)