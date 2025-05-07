from django.conf import settings
from openai import OpenAI  # ✅ NEW IMPORT
import json
from django.http import JsonResponse
from .models import ChatHistory
from django.views import View
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin


client = OpenAI(api_key=settings.OPEN_AI_API_KEY) 
@method_decorator(csrf_exempt, name='dispatch')
class Homepage(LoginRequiredMixin, View):
    template_name = "dashboard/dashboard.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        try:
            data = json.loads(request.body)
            question = data.get("question", "").strip()
            edited_previous = data.get("edited_response", "").strip()

            if not question:
                return JsonResponse({"response": "Question cannot be empty."})

            system_prompt = """
            You are a professional medical MCQ assistant trained to help students prepare for NEET PG, FMGE, and UPSC CMS exams.

            When a multiple-choice question (MCQ) is submitted, follow this structured format **exactly**, using proper spacing, headings, and medical accuracy.

            Always format your response like this:

            ---

            **Final Question (Improved)**  
            <Reword the question for clarity and correctness.>

            **All Options (Improved)**  
            A. <Option A>  
            B. <Option B>  
            C. <Option C>  
            D. <Option D>

            **Correct Answer**  
            C. <Correct Answer Text>

            **Detailed Explanation**  

            ✅ **Explanation of the Correct Answer**  
            <Explain why the correct option is correct using clinical reasoning, mechanisms, or national guidelines. Mention relevant policies like UIP if applicable.>

            ❌ **Explanation of Incorrect Options**  
            A. <Why A is wrong>  
            B. <Why B is wrong>  
            D. <Why D is wrong>

            **Review Synopsis: High-Yield Points on This Topic**  
            - Point 1  
            - Point 2  
            - Point 3  
            - Point 4

            ---

            Your tone should be professional and academic, using medically accepted terms. Always insert line breaks between sections. Do not skip the headings or structure, and never give answers outside of the MCQ format.
            """

            # Proper message list including system role
            messages = [{"role": "system", "content": system_prompt}]
            # Build ChatGPT messages
            messages.append({"role": "user", "content": question})
            if edited_previous:
                messages.append({
                    "role": "user",
                    "content": f"FYI: The previous response was improved by the user as follows:\n\n{edited_previous}\n\nPlease use this to improve your response style."
                })

            response = client.chat.completions.create(
                model = "gpt-4-turbo",
                messages= messages
            )

            # Accessing the response content using dot notation
            response_text = response.choices[0].message.content
            
             # Save both original and edited if provided
            ChatHistory.objects.create(
                question=question,
                response=response_text,
                is_user_edited=bool(edited_previous),
                edited_response=edited_previous if edited_previous else None,
                user = request.user
            )

            return JsonResponse({"response": response_text})
        except Exception as e:
            return JsonResponse({"response": f"Error: {str(e)}"})
