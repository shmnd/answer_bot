from django.db import models
from apps.authentication.models import Users

class MCQ(models.Model):
    qid = models.CharField(max_length=20, unique=True,blank=True, null=True)
    subject = models.CharField(max_length=255,blank=True, null=True)
    question = models.TextField(blank=True, null=True)
    option_a = models.TextField(blank=True, null=True)
    option_b = models.TextField(blank=True, null=True)
    option_c = models.TextField(blank=True, null=True)
    option_d = models.TextField(blank=True, null=True)
    correct_option = models.CharField(max_length=1,blank=True, null=True)
    image_url = models.TextField(blank=True, null=True)
    explanation = models.TextField(blank=True, null=True)



class Questions(models.Model):
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