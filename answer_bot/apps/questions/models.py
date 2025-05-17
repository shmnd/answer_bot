from django.db import models
from apps.authentication.models import Users
# Create your models here.

class Qustions(models.Model):
    user              = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)
    qid               = models.IntegerField(unique=True,blank=True, null=True)
    is_correct        = models.BooleanField(default=True)
    reviewed          = models.BooleanField(default=False)
    question          = models.TextField(blank=True, null=True)
    gpt_answer        = models.TextField(blank=True, null=True)
    new_gpt_answer    = models.TextField(blank=True, null=True)
    correct_answer    = models.CharField(max_length=10, blank=True, null=True)
    explanation       = models.TextField(blank=True, null=True)
    image             = models.ImageField(upload_to='question_images/', blank=True, null=True)
    response          = models.TextField(blank=True, null=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def __str__(self):
        return str(self.pk)
    


class FlaggedQuestion(models.Model):
    qid               = models.IntegerField(unique=True,blank=True, null=True)
    question          = models.TextField()
    existing_answer   = models.CharField(max_length=10)
    uploaded_answer   = models.CharField(max_length=10)
    notes             = models.TextField(blank=True, null=True)
    resolved          = models.BooleanField(default=False)
    reviewed_by       = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.pk)

