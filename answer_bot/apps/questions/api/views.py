import json
import re
import logging
from django.conf import settings
from openai import OpenAI
from bs4 import BeautifulSoup
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.questions.models import Prompt,ImprovedResponse,Keywords,ElasticSearch
from .serializers import MCQSerializer,MCQSearchResultSerializer,GenerateMCQsQuestions
from answer_bot_core.helpers.response import ResponseInfo
from drf_yasg.utils import swagger_auto_schema
from answer_bot_core.helpers.elastic_client import es
from drf_yasg import openapi
from answer_bot_core.helpers.keyword_picker import extract_keyword_from_question
from answer_bot_core.helpers.prompt import build_gpt_prompt,build_gpt_prompt2
logger = logging.getLogger(__name__)


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
                "image_data": validated.get("image_url") or None,
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

            try:
                prompt_template = Prompt.objects.last().prompt
            except AttributeError:
                prompt_template = ""


            prompt_2 = prompt_template.replace("{{payload}}", json.dumps(prompt_2_payload, indent=2))

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
        


# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''' SERACHING BY QUESTION '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
class MCQSearchView(APIView):
    
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(MCQSearchView,self).__init__(**kwargs)

    serializer_class = MCQSearchResultSerializer

    @swagger_auto_schema(
        tags=["Elastic Search"],
        manual_parameters=[
            openapi.Parameter(
                name="name",
                in_=openapi.IN_QUERY,
                description="Search term for MCQs",
                required=True,
                type=openapi.TYPE_STRING
            )
        ]
    )

    def get(self,request):
        try:
            query = request.GET.get('name')

            if not query:
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['message'] = "Query param 'name' is required"
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)
            
            search_keywords = extract_keyword_from_question(query)
            
            # Search in ElasticSearch 
            es_result = es.search(index="mcq_questions",body={
                "query":{
                    "multi_match":{
                        "query":search_keywords,
                        "fields":[
                            "question",
                            # "opa",
                            # "opb",
                            # "opc",
                            # "opd",
                            # "correct_answer",
                            # "explanation",
                        ],
                        "type": "best_fields",
                        "tie_breaker": 0.3
                    }
                }
            })

            # Extract matching question id 
            matched_ids = [hit["_id"] for hit in es_result["hits"]["hits"]]

            # Convert strings id into integers
            matched_ids = [int(i) for i in matched_ids]

            # Fetch full details from DB
            questions = ImprovedResponse.objects.filter(id__in=matched_ids)

            # Serialize manually or with DRF serializer
            serializer = MCQSearchResultSerializer(questions, many=True)

            self.response_format['status_code'] = status.HTTP_200_OK
            self.response_format["message"] = "success"
            self.response_format["status"] = True
            self.response_format["data"] =  serializer.data
            return Response(self.response_format, status=status.HTTP_200_OK)
        
        except Exception as e:
            self.response_format['status_code'] = status.HTTP_500_INTERNAL_SERVER_ERROR
            self.response_format['status'] = False
            self.response_format['message'] = str(e)
            return Response(self.response_format, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''' QUESTION DATA + CHAT GPT ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        
class GenerateMCQSAnswersView(APIView):
    
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(GenerateMCQSAnswersView, self).__init__(**kwargs)

    serializer_class = GenerateMCQsQuestions

    @swagger_auto_schema(
        tags=["GPT+EXISTING EXPM"],
        manual_parameters=[
            openapi.Parameter(
                name="Question",
                in_=openapi.IN_QUERY,
                description="Generate answers for MCQs",
                required=True,
                type=openapi.TYPE_STRING
            )
        ]
    )
    def get(self, request):
        try:
            query = request.GET.get('Question')

            if not query:
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['message'] = "Query param 'Question' is required"
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            search_keywords = extract_keyword_from_question(query)

            es_result = es.search(index="mcq_questions", body={
                "_source": ["qid", "question", "opa", "opb", "opc", "opd", "correct_answer", "explanation"],
                "query": {
                    "multi_match": {
                        "query": search_keywords,
                        "fields": ["question"],
                        "type": "best_fields",
                        "tie_breaker": 0.3
                    }
                },
                "size": 5
            })

            hits = es_result["hits"]["hits"]

            if not hits:
                self.response_format['status'] = False
                self.response_format['message'] = "No matches found. Prompt created without historical context."
                self.response_format['data'] = {
                    "top_score": 0,
                    "total_hits": 0,
                    "good_matches": 0,
                    "gpt_prompt_preview": gpt_prompt.strip()
                }
                return Response(self.response_format, status=status.HTTP_200_OK)

            good_matches = [hit for hit in hits if hit["_score"] >= 10]

            context_blocks = []
            for hit in good_matches:
                source = hit["_source"]
                block = (
                    f"Context (Score: {round(hit['_score'], 2)}):\n"
                    f"subject: {source.get('subject')}\n"
                    f"pearl_title: {source.get('pearl_title')}\n"
                    f"pearl_desc: {source.get('pearl_desc')}"
                )
                context_blocks.append(block.strip())

            if good_matches:
                best_source = good_matches[0]["_source"]
                qid = best_source.get("qid","None")
                opa = best_source.get("opa", "None")
                opb = best_source.get("opb", "None")
                opc = best_source.get("opc", "None")
                opd = best_source.get("opd", "None")
                correct_answer = best_source.get("correct_answer", "None")
                explanation = best_source.get("explanation", "None")
            else:
                opa = opb = opc = opd = correct_answer = explanation = "None"

            # --- Build Prompt ---
            gpt_prompt = build_gpt_prompt(
                query=query,
                context_blocks=context_blocks,
                opa=opa,
                opb=opb,
                opc=opc,
                opd=opd,
                correct_answer=correct_answer,
                explanation=explanation,
            )

            # --- GPT Request ---
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Strictly follow the MCQ editor behavior and output JSON only."},
                    {"role": "user", "content": gpt_prompt},
                ],
                temperature=0.3,
            )
            gpt_result = response.choices[0].message.content

            # --- Parse GPT JSON ---
            try:
                parsed = json.loads(gpt_result)
            except json.JSONDecodeError:
                self.response_format.update({
                    "status": False,
                    "status_code": 500,
                    "message": "GPT returned invalid JSON",
                    "data": {"raw_output": gpt_result}
                })
                return Response(self.response_format, status=500)
            
            # --- Save to DB ---
            qid = request.GET.get("qid")
            qid = int(qid) if qid else None

            filter_kwargs = {"qid": qid} if qid else {"question": query}

            # Clean explanation text
            raw_html = json.dumps(parsed.get("improved_explanation", {}), indent=2)
            clean_exmp = BeautifulSoup(raw_html, "html.parser").get_text().strip().replace('\n', ' ')
            logger.debug(f"{clean_exmp} - cleaned explanation content")

            correct_answer = str(correct_answer).strip().upper()
            if correct_answer not in ["A", "B", "C", "D"]:
                correct_answer = correct_answer[-1:] if correct_answer else None

            gpt_answer = parsed.get("correct_answer", "").strip().upper()
            if gpt_answer not in ["A", "B", "C", "D"]:
                gpt_answer = gpt_answer[-1:] if gpt_answer else None

            ImprovedResponse.objects.update_or_create(
                **filter_kwargs,
                defaults={
                    "question": query,
                    "opa": opa,
                    "opb": opb,
                    "opc": opc,
                    "opd": opd,
                    "correct_answer": correct_answer,
                    "explanation": explanation,
                    "gpt_answer":gpt_answer,
                    "gpt_explanation": parsed.get("improved_explanation"),
                    "improved_question": parsed.get("improved_question"),
                    "improved_opa": parsed.get("improved_options", {}).get("A"),
                    "improved_opb": parsed.get("improved_options", {}).get("B"),
                    "improved_opc": parsed.get("improved_options", {}).get("C"),
                    "improved_opd": parsed.get("improved_options", {}).get("D"),
                    "improved_explanation": clean_exmp,
                    "type": 1,
                    "flag_for_human_review": not parsed.get("improved_correct_answer")
                }
            )

            self.response_format['status'] = True
            self.response_format['message'] = "Relevant MCQs fetched and prompt prepared"
            self.response_format['data'] = {
                "qid": qid,
                "type": 1,
                "new_question": parsed.get("improved_question"),
                "new_op1": parsed.get("improved_options", {}).get("A"),
                "new_op2": parsed.get("improved_options", {}).get("B"),
                "new_op3": parsed.get("improved_options", {}).get("C"),
                "new_op4": parsed.get("improved_options", {}).get("D"),
                "new_cop": parsed.get("correct_answer"),
                "new_expm": parsed.get("improved_explanation"),
                "flag_for_human_review": not bool(parsed.get("correct_answer"))
            }
            return Response(self.response_format, status=status.HTTP_200_OK)

        except Exception as e:            
            self.response_format['status_code'] = status.HTTP_500_INTERNAL_SERVER_ERROR
            self.response_format['status'] = False
            self.response_format['message'] = str(e)
            return Response(self.response_format, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class GenerateAnswersView(APIView):
    
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(GenerateAnswersView, self).__init__(**kwargs)

    serializer_class = GenerateMCQsQuestions

    @swagger_auto_schema(request_body=GenerateMCQsQuestions,tags=["GPT+ES"])

    def post(self, request):
        try:
            serializer = self.serializer_class(data = request.data, context={'request': request})

            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['message'] = "Invalid data"
                self.response_format['errors'] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)
            
            # ✅ Combine all relevant fields into a single string for keyword extraction
            combined_text = " ".join([
                serializer.validated_data.get('question', ''),
                serializer.validated_data.get('opa', ''),
                serializer.validated_data.get('opb', ''),
                serializer.validated_data.get('opc', ''),
                serializer.validated_data.get('opd', ''),
                serializer.validated_data.get('correct_answer', ''),
                serializer.validated_data.get('explanation', ''),
            ])

            keyword_list = extract_keyword_from_question(combined_text)
            logger.info(f"{keyword_list}-000000000000000000000000000000000000000000000000000000000")

            search_string = " ".join(keyword_list) 
            Keywords.objects.create(keywords=keyword_list)

            es_result = es.search(index="db_pearl_m_index", body={
                "_source": ["pid", "subject", "pearl_title", "pearl_desc"],
                "query": {
                    "multi_match": {
                        "query": search_string,
                       "fields": ["subject", "pearl_title", "pearl_desc"],
                        "type": "best_fields",
                        "tie_breaker": 0.3
                    }
                },
                "size": 5
            })

            hits = es_result["hits"]["hits"]
            for i in hits:
                logger.info(f'{i}-iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii')
                ElasticSearch.objects.create(elastic_result=i)

            logger.info(f"{hits}-elastic search dataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

            if not hits:
                self.response_format['status'] = False
                self.response_format['message'] = "No matches found. Prompt created without historical context."
                self.response_format['data'] = {
                    "top_score": 0,
                    "total_hits": 0,
                    "good_matches": 0,
                    "gpt_prompt_preview": gpt_prompt.strip()
                }
                return Response(self.response_format, status=status.HTTP_200_OK)

            good_matches = [hit for hit in hits if hit["_score"] >= 10]

            context_blocks = []
            for hit in good_matches:
                source = hit["_source"]
                block = (
                    f"Context (Score: {round(hit['_score'], 2)}):\n"
                    f"subject: {source.get('subject')}\n"
                    f"pearl_title: {source.get('pearl_title')}\n"
                    f"pearl_desc: {source.get('pearl_desc')}"
                )
                context_blocks.append(block.strip())
            
            if good_matches:
                best_source = good_matches[0]["_source"]
                subject = best_source.get("subject")
                pearl_title = best_source.get("pearl_title")
                pearl_desc = best_source.get("pearl_desc")
            else:
                subject = pearl_title = pearl_desc = "None"

            # --- Build Prompt ---
            gpt_prompt = build_gpt_prompt2(
                question = combined_text,
                context_blocks=context_blocks,
                subject=subject,
                pearl_title=pearl_title,
                pearl_desc=pearl_desc,
            )

            # --- GPT Request ---
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Strictly follow the MCQ editor behavior and output JSON only."},
                    {"role": "user", "content": gpt_prompt},
                ],
                temperature=0.3,
            )
            gpt_result = response.choices[0].message.content

            logger.info(f'{type(gpt_result)}-typeeeeeeeeeeeeeeeeeeeeeeeeeee')

            logger.info(f"{gpt_result}-4444444444444444444444444444444444")

            # --- Parse GPT JSON ---
            try:
                parsed = json.loads(gpt_result)
            except json.JSONDecodeError:
                self.response_format.update({
                    "status": False,
                    "status_code": 500,
                    "message": "GPT returned invalid JSON",
                    "data": {"raw_output": gpt_result}
                })
                return Response(self.response_format, status=500)
            
            # --- Save to DB ---
            # Clean explanation text
            raw_html = json.dumps(parsed.get("improved_explanation", {}), indent=2)
            clean_exmp = BeautifulSoup(raw_html, "html.parser").get_text().strip().replace('\n', ' ')
            logger.info(f"{clean_exmp} - cleaned explanation content -5555555555555555555555555555")

            gpt_answer = parsed.get("correct_answer", "").strip().upper()
            if gpt_answer not in ["A", "B", "C", "D"]:
                gpt_answer = gpt_answer[-1:] if gpt_answer else None

            logger.info(f"{gpt_answer}-6666666666666666666666666")

            ImprovedResponse.objects.update_or_create(
                defaults={
                    "gpt_answer":gpt_answer,
                    "gpt_explanation": parsed.get("improved_explanation"),
                    "improved_question": parsed.get("improved_question"),
                    "improved_opa": parsed.get("improved_options", {}).get("A"),
                    "improved_opb": parsed.get("improved_options", {}).get("B"),
                    "improved_opc": parsed.get("improved_options", {}).get("C"),
                    "improved_opd": parsed.get("improved_options", {}).get("D"),
                    "improved_explanation": clean_exmp,
                    "type": 1,
                    "flag_for_human_review": not parsed.get("improved_correct_answer")
                }
            )

            self.response_format['status'] = True
            self.response_format['message'] = "Relevant MCQs fetched and prompt prepared"
            self.response_format['data'] = {
                "type": 1,
                "new_question": parsed.get("improved_question"),
                "new_op1": parsed.get("improved_options", {}).get("A"),
                "new_op2": parsed.get("improved_options", {}).get("B"),
                "new_op3": parsed.get("improved_options", {}).get("C"),
                "new_op4": parsed.get("improved_options", {}).get("D"),
                "new_cop": parsed.get("correct_answer"),
                "new_expm": parsed.get("improved_explanation"),
                "flag_for_human_review": not bool(parsed.get("correct_answer"))
            }
            return Response(self.response_format, status=status.HTTP_200_OK)

        except Exception as e:            
            self.response_format['status_code'] = status.HTTP_500_INTERNAL_SERVER_ERROR
            self.response_format['status'] = False
            self.response_format['message'] = str(e)
            return Response(self.response_format, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
