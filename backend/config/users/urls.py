from django.urls import path
from .views import register_view, login_view, UserMeView, LogoutView

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('me/', UserMeView.as_view(), name='me'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
