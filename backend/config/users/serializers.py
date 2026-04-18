from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Profile

User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('faculty', 'phone', 'bio')

class UserSerializer(serializers.ModelSerializer):
    faculty = serializers.CharField(source='profile.faculty', read_only=True, default='')
    phone = serializers.CharField(source='profile.phone', read_only=True, default='')
    bio = serializers.CharField(source='profile.bio', read_only=True, default='')
    avatar = serializers.ImageField(source='profile.avatar', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'student_id', 'first_name', 'last_name', 'faculty', 'phone', 'bio', 'avatar')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    faculty = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'student_id', 'first_name', 'last_name', 'password', 'faculty', 'phone')

    def create(self, validated_data):
        faculty = validated_data.pop('faculty', '')
        phone = validated_data.pop('phone', '')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            student_id=validated_data['student_id'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password']
        )
        
        Profile.objects.create(user=user, faculty=faculty, phone=phone)
        return user

class LoginSerializer(serializers.Serializer):
    login = serializers.CharField() # Can be email or student_id
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        login = data.get('login')
        password = data.get('password')

        if not login or not password:
            raise serializers.ValidationError('Must include "login" and "password".')

        user = None
        if '@' in login:
            user = User.objects.filter(email=login).first()
        else:
            user = User.objects.filter(student_id=login).first()

        if user is None:
            raise serializers.ValidationError('Invalid login credentials.')

        if not user.check_password(password):
            raise serializers.ValidationError('Invalid login credentials.')

        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')

        refresh = RefreshToken.for_user(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }
