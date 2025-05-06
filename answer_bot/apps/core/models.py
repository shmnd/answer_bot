from django.db import models
from apps.authentication.models import Users

# Create your models here.

class ChatHistory(models.Model):
    qid = models.CharField(max_length=100, unique=True,blank=True, null=True)
    question = models.TextField(blank=True, null=True)
    gpt_answer = models.TextField(blank=True, null=True)
    edited_answer = models.TextField(blank=True, null=True)
    improved_gpt_answer = models.TextField(blank=True, null=True)  # New
    user = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)
    response = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_user_edited = models.BooleanField(default=False)
    edited_response = models.TextField(blank=True, null=True)
