from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Count

from .models import Post
from .serializers import PostSerializer

User = get_user_model()

class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Post.objects.select_related('author', 'author__profile')
        if self.action in {'retrieve', 'update', 'partial_update', 'destroy', 'reply', 'like', 'save', 'rescrawl'}:
            return queryset
        if self.action == 'my_posts':
            return queryset.filter(
                author=self.request.user,
                parent__isnull=True,
                is_anonymous=False
            )
        if self.action == 'user_posts':
            return queryset.filter(
                author_id=self.kwargs.get('user_id'),
                parent__isnull=True,
                is_anonymous=False
            )
        if self.action == 'saved':
            return queryset.filter(saved_by=self.request.user, parent__isnull=True)
        if self.action == 'rescrawled':
            return queryset.filter(rescrawls=self.request.user, parent__isnull=True)
        if self.action == 'user_rescrawled':
            return queryset.filter(
                rescrawls__id=self.kwargs.get('user_id'),
                parent__isnull=True
            ).distinct()
        if self.action == 'replies':
            return queryset.filter(parent_id=self.kwargs.get('pk'))
        # For list action, filter by faculty if provided
        if self.action == 'list':
            faculty = self.request.query_params.get('faculty')
            if faculty and faculty != 'all':
                queryset = queryset.filter(faculty=faculty)
            return queryset.filter(parent__isnull=True).order_by('-created_at')
        return queryset.filter(parent__isnull=True).order_by('-created_at')

    def get_permissions(self):
        if self.action in {'list', 'retrieve', 'user_posts', 'user_rescrawled', 'replies'}:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _sync_counts(self, post):
        post.likes_count = post.likes.count()
        post.saves_count = post.saved_by.count()
        post.rescralws_count = post.rescrawls.count()
        post.save(update_fields=['likes_count', 'saves_count', 'rescralws_count', 'updated_at'])

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user:
            return Response({'detail': 'You do not have permission to edit this post.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user:
            return Response({'detail': 'You do not have permission to edit this post.'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        if post.likes.filter(pk=request.user.pk).exists():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True
        self._sync_counts(post)
        return Response({'liked': liked, 'likes_count': post.likes_count})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def save(self, request, pk=None):
        post = self.get_object()
        if post.saved_by.filter(pk=request.user.pk).exists():
            post.saved_by.remove(request.user)
            saved = False
        else:
            post.saved_by.add(request.user)
            saved = True
        self._sync_counts(post)
        return Response({'saved': saved, 'saves_count': post.saves_count})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='rescrawl')
    def rescrawl(self, request, pk=None):
        post = self.get_object()
        if post.rescrawls.filter(pk=request.user.pk).exists():
            post.rescrawls.remove(request.user)
            rescrawled = False
        else:
            post.rescrawls.add(request.user)
            rescrawled = True
        self._sync_counts(post)
        return Response({'rescrawled': rescrawled, 'rescralws_count': post.rescralws_count})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='me')
    def my_posts(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny], url_path=r'user/(?P<user_id>\d+)')
    def user_posts(self, request, user_id=None):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='saved')
    def saved(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='rescrawled')
    def rescrawled(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny], url_path=r'user/(?P<user_id>\d+)/rescrawled')
    def user_rescrawled(self, request, user_id=None):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='reply')
    def reply(self, request, pk=None):
        parent_post = self.get_object()
        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'content': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            'content': content,
            'mood': request.data.get('mood', ''),
            'is_anonymous': request.data.get('is_anonymous', False),
            'parent': parent_post.pk,
        }
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny], url_path='replies')
    def replies(self, request, pk=None):
        queryset = self.get_queryset().order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class UserStatsView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        posts_count = Post.objects.filter(author=user).count()
        return Response(
            {
                'posts_count': posts_count,
                'followers_count': 0,
                'following_count': 0,
            },
            status=status.HTTP_200_OK,
        )


@api_view(['GET'])
def community_counts(request):
    """Get post counts for each faculty/community"""
    data = Post.objects.values('faculty').annotate(count=Count('id')).order_by('-count')
    # Convert to dict with faculty as key for easier frontend consumption
    result = {item['faculty']: item['count'] for item in data}
    return Response(result)
