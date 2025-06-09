from django.urls import path
from . import views

urlpatterns = [

    path('questions-process/', views.ProcessMCQView.as_view(), name='process-mcq'),
    path("search-mcq/", views.MCQSearchView.as_view(), name="search-mcq"),
    path("generate-mcq/",views.GenerateMCQSAnswersView.as_view(),name="Gemerate-mcq"),

    
    path("mcq/",views.GenerateAnswersView.as_view(),name="mcq")

]