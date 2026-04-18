from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, LoginSerializer, UserSerializer

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
