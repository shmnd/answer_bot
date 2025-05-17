from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
app_name = 'questions'


urlpatterns = [
    path('',login_required(views.QuestionPrompt.as_view()),name='qusetion-prompt'),
]