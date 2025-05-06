from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
# Create your views here.
class Homepage(LoginRequiredMixin,View):
    
    def __init__(self):
        self.response_format = {'status_code':101,'message':'','error':''}

    template_name = "dashboard/dashboard.html"

    def get(self,request):



        return render(request,self.template_name)
    