import json
import re
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
            
            serializer = self.serializer_class(data = request.data, context={'request': request})
            
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format["status"] = False
                self.response_format["errors"] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)
            
            # Step 1: Save original to DB
            validated = serializer.validated_data
            instance = serializer.save()

            # Step 1: Prompt 1 - get GPT answer
            question = validated.get("question")
            options = {
                "A": validated.get("opa"),
                "B": validated.get("opb"),
                "C": validated.get("opc"),
                "D": validated.get("opd"),
            }

            prompt_1_payload = {
                "question_text": question,
                "options": {
                    "A": options["A"],
                    "B": options["B"],
                    "C": options["C"],
                    "D": options["D"]
                }
            }

            prompt_1 = f"""
                You are a clinical MCQ assistant.

                I will provide an MCQ in JSON format. You must identify the correct answer (A–D) and provide a concise, medically accurate explanation.

                Here is the MCQ:

                {json.dumps(prompt_1_payload, indent=2)}

                Instructions:
                - First, analyze the question and all options.
                - Then respond in this format:

                Answer: <A/B/C/D>

                Explanation: <your reasoning>
                """

            response_1 = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Answer the medical MCQ with reasoning."},
                    {"role": "user", "content": prompt_1}
                ]
            )
            gpt_response = response_1.choices[0].message.content.strip()

            # Extract answer letter
            
            match = re.search(r"(?i)answer[:\-]?\s*([A-D])", gpt_response)
            gpt_answer_letter = match.group(1).upper() if match else None

            instance.gpt_answer = gpt_answer_letter
            instance.gpt_explanation = gpt_response
            instance.save()

            if not gpt_answer_letter or gpt_answer_letter != validated.get('correct_answer',"").strip().upper():
                instance.flag_for_human_review = True
                instance.save()

                self.response_format['status'] = True
                self.response_format['message'] = "Flagged for human review"
                self.response_format["data"] = {
                    "qid": instance.qid,
                    "type": instance.type,
                    "flag_for_human_review": instance.flag_for_human_review
                }
                return Response(self.response_format, status=status.HTTP_200_OK)
            
            # Step 3: Prompt 2 — Improve question using both inputs

            prompt_2_payload = {
                "question_text": question,
                "image_data": validated.get("image_url") or None,
                "options": {
                    "A": options['A'],
                    "B": options['B'],
                    "C": options['C'],
                    "D": options['D']
                },
                "system_answer": validated.get("correct_answer"),
                "system_explanation": validated.get("explanation"),
                "chatgpt_explanation": gpt_response,
                "create_newer_version": validated.get("type", 1) # or 0 depending on your UI/API input
            }

            prompt_2 = f"""
                You are an expert clinical-MCQ editor and validator. I will provide the following fields in JSON:

                {json.dumps(prompt_2_payload, indent=2)}

                Do the following:
                1. *Validate*  
                - Extract the answer letter from chatgpt_explanation.  
                - If it does *not* match system_answer, output exactly:
                    json
                    {{ "flag_for_human_review": true }}

                - Otherwise continue to step 2.

                2. *Question & Options*  
                - If create_newer_version == 1:  
                    • Rewrite the stem for clarity and precision; expand all acronyms; fix grammar; avoid any potential copyright overlap.  
                    • Rewrite each option (A–D) to remove duplicates, correct spelling/grammar, and keep clinical accuracy.  
                - If create_newer_version == 0:  
                    • Keep the stem and options as close to the original as possible, but correct any typos, expand acronyms, and polish grammar.

                3. *Explanation*  
                - Merge system_explanation and chatgpt_explanation, selecting the best content from each into one structured explanation object:  
                    json
                    {{
                    "overview": "...",
                    "correct_option": "...",
                    "others": {{ "A": "...", "B": "...", "D": "..." }}
                    }}

                4. *Output*  
                - Return a single JSON object. If validated, the object must contain:
                    json
                    {{
                    "improved_question": "...",
                    "improved_options": {{
                        "A": "...",
                        "B": "...",
                        "C": "...",
                        "D": "..."
                    }},
                    "correct_answer": "C",
                    "improved_explanation": {{
                        "overview": "...",
                        "correct_option": "...",
                        "others": {{ "A": "...", "B": "...", "D": "..." }}
                    }}
                    }}
                - If flagged, only output {{ "flag_for_human_review": true }} and no other keys.
                """

            response_2 = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Strictly follow the MCQ editor behavior and output JSON only."},
                    {"role": "user", "content": prompt_2}
                ]
            )

            try:
                improved_output = response_2.choices[0].message.content.strip()

                # Strip code block if GPT returns markdown style
                if improved_output.startswith("```json"):
                    improved_output = re.sub(r"^```json|```$", "", improved_output.strip(), flags=re.IGNORECASE).strip()
                elif improved_output.startswith("```"):
                    improved_output = re.sub(r"^```|```$", "", improved_output.strip()).strip()

                improved_data = json.loads(improved_output)

                update_type = validated.get("type", 1)

                if update_type == 1:

                    # Step 3: Save improved values
                    instance.improved_question = improved_data.get("improved_question")
                    options = improved_data.get("improved_options", {})
                    instance.improved_opa = options.get("A")
                    instance.improved_opb = options.get("B")
                    instance.improved_opc = options.get("C")
                    instance.improved_opd = options.get("D")
                    instance.correct_answer = improved_data.get("correct_answer")
                else:
                    # Only return original data in the response, don't update question/options
                    instance.improved_question = validated.get('question')
                    instance.improved_opa = validated.get("opa")
                    instance.improved_opb = validated.get("opb")
                    instance.improved_opc = validated.get("opc")
                    instance.improved_opd = validated.get("opd")
                    instance.correct_answer = validated.get("correct_answer")

                # Always update explanation regardless of type
                instance.improved_explanation = json.dumps(improved_data.get("improved_explanation", {}), indent=2)
                instance.is_verified = True
                instance.save()

                self.response_format['status_code'] = status.HTTP_201_CREATED
                self.response_format["message"] = "success"
                self.response_format["status"] = True
                self.response_format["data"] = {
                    "qid": instance.qid,
                    "type": instance.type,
                    "new_question": instance.improved_question,
                    "new_op1": instance.improved_opa,
                    "new_op2": instance.improved_opb,
                    "new_op3": instance.improved_opc,
                    "new_op4": instance.improved_opd,
                    "new_cop": instance.correct_answer,
                    "new_expm": json.loads(instance.improved_explanation) if instance.improved_explanation else {},
                    "flag_for_human_review": instance.flag_for_human_review
                }
                return Response(self.response_format, status=status.HTTP_201_CREATED)

            except Exception as e:
                self.response_format['status_code'] = status.HTTP_422_UNPROCESSABLE_ENTITY
                self.response_format['status'] = False
                self.response_format['message'] = "GPT response was not valid JSON"
                return Response(self.response_format, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
        except Exception as e:
            self.response_format['status_code'] = status.HTTP_500_INTERNAL_SERVER_ERROR
            self.response_format['status'] = False
            self.response_format['message'] = str(e)
            return Response(self.response_format, status=status.HTTP_500_INTERNAL_SERVER_ERROR)