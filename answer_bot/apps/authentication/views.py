from django.shortcuts import render,redirect
from django.views import View
from apps.authentication.models import Users
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.contrib.auth import login,logout,authenticate
# Create your views here.


class UserRegistrationView(View):

    def __init__(self):
        self.response_format = {'status_code':101,'message':'','error':''}

    template_name = "authentication/signup.html"

    def get(self,request):
        return render(request,self.template_name)
    
    def post(self,request):
        try:
            email = request.POST.get('email')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            if Users.objects.filter(email=email).exists():
                return JsonResponse({'status_code':200,'message':'Email already exists'},status=400)
            
            if password != confirm_password:
                return JsonResponse({'status':200,'message':'Password does not match'},status=400)
            
            user = Users.objects.create(
                email=email,
                password = make_password(password),
                is_active = True,
            )

            login_url = reverse("authentication:login")

            return JsonResponse({
                'status_code':100,
                'message':'Signup Successfull',
                'redirect_url': login_url
            },status=200)

        except Exception as e:
            return JsonResponse({
                'status':500,
                'message':"Something went wrong",
                'error':str(e)
            },status=500)
        


class UserLoginView(View):

    def __init__(self):
        self.response_format = {'status_code':101,'message':'','error':''}

    def get(self,request, *args, **kwargs):
        return render(request,'authentication/login.html')
    
    def post(self, request, *args, **kwargs):
    
        try:
            email       = request.POST.get('email')
            password    = request.POST.get('password')
            user        = authenticate(request,email=email, password=password)

            homer_url = reverse("home:dashboard")

            if user is not None:
                login(request, user)
                return JsonResponse({
                        "status_code": 100,
                        "message": "Login successfully. Redirecting...",
                        "redirect_url": homer_url 
                    }, status=200)
            
            else:
                self.response_format['message'] = 'Invalid email or password'

        except Exception as e:
            self.response_format['message'] = 'Something went wrong, Please try again later.'
            self.response_format['error'] = str(e)

        return JsonResponse(self.response_format, status=200)
    
def signout(request):    
    logout(request)
    return redirect('authentication:login')



