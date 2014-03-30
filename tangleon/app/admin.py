"""
Django admin entities of TangleOn
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""

from django.contrib import admin

from tangleon.app.models import User, Channel, Post, Subscription, Tag, Pin, Comment, PostVote, CommentVote

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'has_activated', 'created_on',)
    list_filter = ( 'is_active', 'is_active', 'has_activated', 'created_on',)
    search_fields = ('username', 'email',)
    date_hierarchy = 'created_on'


class ChannelAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_default', 'is_muted', 'sync_on', 'created_on',)
    list_filter = ('is_default', 'sync_on', 'published', 'created_on',)
    search_fields = ('title',)
    date_hierarchy = 'published'
    ordering = ('-published',)


class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'link', 'votes', 'up_votes', 'down_votes', 'rank',)
    list_filter = ('is_muted', 'published', 'created_on',)
    search_fields = ('post_id', 'title', 'author', 'tags', 'slug',)
    date_hierarchy = 'published'
    ordering = ('-published',)


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel', 'created_on',)
    list_filter =  ('created_on', 'channel',)
    search_fields =  ('user__user_id', 'user__username', 'channel__channel_id', 'channel__title',)
    date_hierarchy = 'created_on'
    ordering = ('-created_on',)
 

class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'is_muted',)
    list_filter =  ('name', 'is_default', 'is_muted',)
    search_fields =  ('tag_id', 'name', 'is_muted',)
    date_hierarchy = 'updated_on'
    ordering = ('tag_id',)


class PinAdmin(admin.ModelAdmin):
    list_display = ('user', 'tag',)
    list_filter =  ('tag',)
    search_fields =  ('user__user_id', 'user__username', 'tag__tag_id', 'tag__name',)
    date_hierarchy = 'created_on'
    ordering = ('-created_on',)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'comment_text', 'reply_count',)
    list_filter = ('reply_count', 'is_muted',)
    search_fields = ('post__post_id', 'post__title', 'comment_text', 'user__user_id', 'user__username',)
    date_hierarchy = 'created_on'
    ordering = ('-created_on',)
 

class PostVoteAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'vote', 'created_on')
    list_filter = ('post', 'user', 'created_on')
    search_fields = ('post__post_id', 'post__title', 'user__user_id', 'user__username',)
    date_hierarchy = 'created_on'
    ordering = ('-created_on',)
    

class CommentVoteAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'vote', 'created_on')
    list_filter = ('comment', 'user', 'created_on')
    search_fields = ('comment__comment_id', 'comment__comment_text', 'user__user_id', 'user__username',)
    date_hierarchy = 'created_on'
    ordering = ('-created_on',)


admin.site.register(User, UserAdmin)
admin.site.register(Channel, ChannelAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Pin, PinAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(PostVote, PostVoteAdmin)
admin.site.register(CommentVote, CommentVoteAdmin)

