from django.contrib import admin
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'content_preview', 'mood', 'is_anonymous', 'created_at')
    list_filter = ('mood', 'is_anonymous', 'created_at')
    search_fields = ('author__username', 'content')
    ordering = ('-created_at',)

    def content_preview(self, obj):
        return obj.content[:60] + '...' if len(obj.content) > 60 else obj.content
    content_preview.short_description = 'Content'
