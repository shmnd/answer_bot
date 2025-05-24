from django.db import models
from apps.authentication.models import Users
# Create your models here.

class ImprovedResponse(models.Model):
    qid                     = models.IntegerField(blank=True, null=True)
    question                = models.TextField(blank=True, null=True)
    opa                     = models.TextField(blank=True, null=True)
    opb                     = models.TextField(blank=True, null=True)
    opc                     = models.TextField(blank=True, null=True)
    opd                     = models.TextField(blank=True, null=True)
    correct_answer          = models.CharField(max_length=1,blank=True, null=True)
    explanation             = models.TextField(blank=True, null=True)
    gpt_answer              = models.TextField(blank=True, null=True)
    gpt_explanation         = models.TextField(blank=True, null=True)
    improved_question       = models.TextField(blank=True, null=True)
    improved_opa            = models.TextField(blank=True, null=True)
    improved_opb            = models.TextField(blank=True, null=True)
    improved_opc            = models.TextField(blank=True, null=True)
    improved_opd            = models.TextField(blank=True, null=True)
    improved_explanation    = models.TextField(blank=True, null=True)
    is_verified             = models.BooleanField(default=False)
    created_at              = models.DateTimeField(auto_now_add=True)
    last_reviewed           = models.DateTimeField(auto_now_add=True)
    type                    = models.IntegerField(blank=True, null=True)
    flag_for_human_review   = models.BooleanField(default=False)


    class Meta:
        verbose_name = "ImprovedResponse"
        verbose_name_plural = "ImprovedResponses"

    def __str__(self):
        return str(self.pk)
    

class Prompt(models.Model):
    prompt = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Prompt"
        verbose_name_plural = "Prompts"

    def __str__(self):
        return str(self.prompt)
    


class FlaggedQuestion(models.Model):
    qid               = models.IntegerField(unique=True,blank=True, null=True)
    question          = models.TextField()
    existing_answer   = models.CharField(max_length=10)
    uploaded_answer   = models.CharField(max_length=10)
    notes             = models.TextField(blank=True, null=True)
    resolved          = models.BooleanField(default=False)
    reviewed_by       = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    # original          = models.ForeignKey(Questions, null=True, on_delete=models.SET_NULL)ImprovedResponse
    reviewed          = models.BooleanField(default=False)

    def __str__(self):
        return str(self.pk)

