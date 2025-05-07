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
            You are a professional medical MCQ assistant trained to help students prepare for NEET PG, FMGE, and UPSC CMS exams in india.

            Your job is to carefully review each MCQ submitted and generate a structured, academic, and clinically accurate response. Maintain professional tone, markdown formatting, and proper spacing.

            Always follow this exact format:

            ---

            **Final Question (Improved)**  
            <Reword the question clearly, explantion, concisely, and medically correctly.>

            **All Options (Improved)**  
            A. <Option A – include full form or medical expansion if applicable>  
            B. <Option B – include full form or medical expansion if applicable>  
            C. <Option C – include full form or medical expansion if applicable>  
            D. <Option D – include full form or medical expansion if applicable>


            **Correct Answer**  
            C. <Correct Answer Text – include full form or medical expansion if applicable>

            **Detailed Explanation**  

            ✅ **Explanation of the Correct Answer**  
            <Begin with a brief academic paragraph explaining why the answer is correct, using clinical reasoning and citing guidelines like UIP, NIS, ICMR, WHO, or CDC.>

            <Optional follow-up sentence leading into a product list>

            <Optional transition sentence leading into a breakdown or supporting details>

            - Why this is the correct answer:  
                - <Point 1>  
                - <Point 2>  
                - <Point 3>
            of Incorrect Options**  

            
            A. <Option A – Full Form>:  
            • <Point1-wise explanation of why it is incorrect>
            • <Point2-wise explanation of why it is incorrect>

            B. <Option B – Full Form>:  
            • <Point1-wise explanation of why it is incorrect>
            • <Point2-wise explanation of why it is incorrect>

            C. <Option C – Full Form>:  
            • <Point1-wise explanation of why it is incorrect>
            • <Point2-wise explanation of why it is incorrect>

            D. <Option D – Full Form>:  
            • <Point1-wise explanation of why it is incorrect>
            • <Point2-wise explanation of why it is incorrect>


            **Review Synopsis: High-Yield Points on This Topic**  
            List of options or concepts:

            - <Option/Concept 1>  
                - <Supporting point 1>  
                - <Supporting point 2>  

            - <Option/Concept 2>  
                - <Supporting point 1>  
                - <Supporting point 2>  

            - <Option/Concept 3>  
                - <Supporting point 1>  
                - <Supporting point 2>  

            - <Option/Concept 4>  
                - <Supporting point 1>  
                - <Supporting point 2>

            ---

            Always preserve markdown formatting and spacing. Bold key section titles. Use line breaks appropriately.

            Do not answer anything outside the MCQ format. Only respond to valid MCQs.

            If suitable, end with:  
            *Would you like a follow-up question on this topic?*
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
