from django.urls import path
from . import views

urlpatterns = [

    path('questions-process/', views.ProcessMCQView.as_view(), name='process-mcq'),

]