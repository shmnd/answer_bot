# urls.py
from django.urls import path
from .views import convert_mcqs
app_name = "convertor"
urlpatterns = [
    path('convert/',convert_mcqs, name='convert-mcqs'),
]