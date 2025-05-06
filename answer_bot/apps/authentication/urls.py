from django.urls import path,re_path
from apps.authentication import views

app_name = "authentication"

urlpatterns = [
    path('signup/',views.UserRegistrationView.as_view(),name='signup'),
    path('login/',views.UserLoginView.as_view(),name='login'),

    re_path(r'^logout',views.signout,name='logout')
]

