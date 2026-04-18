from django.urls import path
from .views import (
    register_view, login_view, UserMeView, LogoutView,
    FollowToggleView, FollowersView, FollowingView, FollowStatusView, FollowCountsView,
    UserByUsernameView
)

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('me/', UserMeView.as_view(), name='me'),
    path('logout/', LogoutView.as_view(), name='logout'),
    # User lookup by username
    path('by-username/<str:username>/', UserByUsernameView.as_view(), name='user-by-username'),
    # Follow endpoints
    path('<int:user_id>/follow/', FollowToggleView.as_view(), name='follow-toggle'),
    path('<int:user_id>/followers/', FollowersView.as_view(), name='followers'),
    path('<int:user_id>/following/', FollowingView.as_view(), name='following'),
    path('<int:user_id>/follow-status/', FollowStatusView.as_view(), name='follow-status'),
    path('<int:user_id>/follow-counts/', FollowCountsView.as_view(), name='follow-counts'),
]
