from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
app_name = 'questions'


urlpatterns = [
    path('',login_required(views.QuestionPrompt.as_view()),name='qusetion-prompt'),

    #prompt
    path("prompt/", views.prompt_list_create_view, name="prompt_module"),
    path("lead/delete/<int:pk>/", views.delete_prompt, name="delete_prompt"),
    path("lead/update/<int:pk>/", views.update_prompt, name="update_prompt"),
]