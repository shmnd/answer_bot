from django.db import models

# Create your models here.
from django.db import models

class MCQ(models.Model):
    qid = models.CharField(max_length=20, unique=True,blank=True, null=True)
    subject = models.CharField(max_length=255,blank=True, null=True)
    question = models.TextField(blank=True, null=True)
    option_a = models.TextField(blank=True, null=True)
    option_b = models.TextField(blank=True, null=True)
    option_c = models.TextField(blank=True, null=True)
    option_d = models.TextField(blank=True, null=True)
    correct_option = models.CharField(max_length=1,blank=True, null=True)
    explanation = models.TextField(blank=True, null=True)
