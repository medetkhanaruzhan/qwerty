from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, SimpleUserSerializer, UserProfileSerializer
from .models import Follow

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': 'User registered successfully.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Validation failed',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
    # If the error is 'Invalid login credentials.', return 401
    errors = serializer.errors
    if 'non_field_errors' in errors and any('Invalid login' in str(e) for e in errors['non_field_errors']):
        return Response({
            'message': 'Invalid login credentials.'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response({
        'message': 'Validation failed',
        'errors': errors
    }, status=status.HTTP_400_BAD_REQUEST)


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        profile = user.profile

        # Update User model fields
        user_fields = ['first_name', 'last_name']
        user_changed = False
        for field in user_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
                user_changed = True
        if user_changed:
            user.save()

        # Update Profile model fields
        profile_fields = ['bio', 'phone', 'faculty']
        profile_changed = False
        for field in profile_fields:
            if field in request.data:
                setattr(profile, field, request.data[field])
                profile_changed = True

        # Handle avatar file upload
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
            profile_changed = True

        if profile_changed:
            profile.save()

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            # If blacklisting fails, we still return 200 because frontend handles logout locally anyway
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)


class FollowToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            print(f"[FollowToggle] user_id={user_id}, request.user={request.user}")
            target_user = get_object_or_404(User, id=user_id)

            if request.user == target_user:
                return Response({"detail": "Cannot follow yourself"}, status=400)

            follow, created = Follow.objects.get_or_create(
                follower=request.user,
                following=target_user
            )

            if not created:
                follow.delete()
                return Response({"is_following": False})

            return Response({"is_following": True})
        except Exception as e:
            print(f"[FollowToggle] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"detail": f"Server error: {str(e)}"}, status=500)


class FollowersView(APIView):
    """Get list of users who follow this user"""
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        try:
            target_user = get_object_or_404(User, id=user_id)
            # Users where target_user is in their 'following' (they follow target_user)
            followers = User.objects.filter(
                following__following=target_user
            ).select_related('profile').distinct()
            serializer = SimpleUserSerializer(followers, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"[FollowersView] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"detail": f"Server error: {str(e)}"}, status=500)


class FollowingView(APIView):
    """Get list of users this user follows"""
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        try:
            target_user = get_object_or_404(User, id=user_id)
            # Users where target_user is in their 'followers' (target_user follows them)
            following = User.objects.filter(
                followers__follower=target_user
            ).select_related('profile').distinct()
            serializer = SimpleUserSerializer(following, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"[FollowingView] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"detail": f"Server error: {str(e)}"}, status=500)


class FollowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            print(f"[FollowStatus] user_id={user_id}, request.user={request.user}")
            target_user = get_object_or_404(User, id=user_id)

            is_following = Follow.objects.filter(
                follower=request.user,
                following=target_user
            ).exists()

            return Response({"is_following": is_following})
        except Exception as e:
            print(f"[FollowStatus] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"detail": f"Server error: {str(e)}"}, status=500)


class FollowCountsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        try:
            print(f"[FollowCounts] user_id={user_id}")
            target_user = get_object_or_404(User, id=user_id)

            followers_count = Follow.objects.filter(following=target_user).count()
            following_count = Follow.objects.filter(follower=target_user).count()

            return Response({
                "followers_count": followers_count,
                "following_count": following_count,
            })
        except Exception as e:
            print(f"[FollowCounts] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"detail": f"Server error: {str(e)}"}, status=500)


class UserByUsernameView(APIView):
    """Get user profile by username"""
    permission_classes = [AllowAny]

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
