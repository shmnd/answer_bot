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


client = OpenAI(api_key=settings.OPEN_AI_API_KEY1) 
@method_decorator(csrf_exempt, name='dispatch')
class Homepage(LoginRequiredMixin, View):
    template_name = "dashboard/dashboard.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        try:
            data = json.loads(request.body)
            question = data.get("question", "")

            if not question.strip():
                return JsonResponse({"response": "Question cannot be empty."})

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": question}]
            )

            # Accessing the response content using dot notation
            response_text = response.choices[0].message.content
            ChatHistory.objects.create(question=question, response=response_text)

            return JsonResponse({"response": response_text})
        except Exception as e:
            return JsonResponse({"response": f"Error: {str(e)}"})
