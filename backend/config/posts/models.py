from django.db import models
from django.conf import settings


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    content = models.TextField()
    mood = models.CharField(max_length=20, blank=True, default='')
    is_anonymous = models.BooleanField(default=False)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='replies',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='liked_posts',
        blank=True,
    )
    saved_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='saved_posts',
        blank=True,
    )
    rescrawls = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='rescrawled_posts',
        blank=True,
    )
    likes_count = models.PositiveIntegerField(default=0)
    saves_count = models.PositiveIntegerField(default=0)
    rescralws_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author.username}: {self.content[:50]}'
