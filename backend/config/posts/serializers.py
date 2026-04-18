from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post

User = get_user_model()


class PostAuthorSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'avatar')

    def get_avatar(self, obj):
        try:
            profile = obj.profile
            if profile.avatar:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.avatar.url)
                return profile.avatar.url
        except Exception:
            pass
        return None


class PostSerializer(serializers.ModelSerializer):
    author = PostAuthorSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    is_rescrawled = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    is_reply = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            'id',
            'content',
            'mood',
            'is_anonymous',
            'parent',
            'created_at',
            'updated_at',
            'author',
            'is_liked',
            'is_saved',
            'is_rescrawled',
            'replies_count',
            'is_reply',
            'likes_count',
            'saves_count',
            'rescralws_count',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'author',
            'is_liked',
            'is_saved',
            'is_rescrawled',
            'replies_count',
            'is_reply',
            'likes_count',
            'saves_count',
            'rescralws_count',
        )

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)

    def _get_user(self):
        request = self.context.get('request')
        if not request:
            return None
        user = request.user
        if not user or not user.is_authenticated:
            return None
        return user

    def get_is_liked(self, obj):
        user = self._get_user()
        if not user:
            return False
        return obj.likes.filter(pk=user.pk).exists()

    def get_is_saved(self, obj):
        user = self._get_user()
        if not user:
            return False
        return obj.saved_by.filter(pk=user.pk).exists()

    def get_is_rescrawled(self, obj):
        user = self._get_user()
        if not user:
            return False
        return obj.rescrawls.filter(pk=user.pk).exists()

    def get_replies_count(self, obj):
        return obj.replies.count()

    def get_is_reply(self, obj):
        return obj.parent_id is not None
