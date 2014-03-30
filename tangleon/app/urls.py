"""
Urls module for all app pages
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns('tangleon.app.views',
                        url(r'^$', 'index', name='app_index'),
                        url(r'^(?P<page_index>\d+)/$', 'index', name='app_index'),
                        url(r'^new/$', 'index', { 'by_new': True },  name='app_index_new'),
                        url(r'^new/(?P<page_index>\d+)/$', 'index', { 'by_new': True }, name='app_index_new'),
                        url(r'^tag/(?P<tag_name>[\w\.@]+)/$', 'tag_posts', name='app_tag'),
                        url(r'^tag/(?P<tag_name>[\w\.@]+)/(?P<page_index>\d+)/$', 'tag_posts', name='app_tag'),
                        url(r'^tag/(?P<tag_name>[\w\.@]+)/new/$', 'tag_posts', { 'by_new': True, 'page_index':0 }, name='app_tag_new'),
                        url(r'^tag/(?P<tag_name>[\w\.@]+)/new/(?P<page_index>\d+)/$', 'tag_posts', { 'by_new': True}, name='app_tag_new'),
                        url(r'^channel/(?P<channel_id>\d+)/$', 'channel_posts', name='app_channel'),
                        url(r'^channel/(?P<channel_id>\d+)/(?P<page_index>\d+)/$', 'channel_posts', name='app_channel'),
                        url(r'^channel/(?P<channel_id>\d+)/new/$', 'channel_posts', { 'by_new':True }, name='app_channel_new'),
                        url(r'^channel/(?P<channel_id>\d+)/new/(?P<page_index>\d+)/$', 'channel_posts', {'by_new': True}, name='app_channel_new'),
                        url(r'^user/(?P<username>[\w\.]+)/$', 'user_posts', name='app_user'),
                        url(r'^user/(?P<username>[\w\.]+)/(?P<page_index>\d+)/$', 'user_posts', name='app_user'),
                        url(r'^user/(?P<username>[\w\.]+)/new/$', 'user_posts', { 'by_new':True }, name='app_user_new'),
                        url(r'^user/(?P<username>[\w\.]+)/new/(?P<page_index>\d+)/$', 'user_posts', {'by_new': True}, name='app_user_new'),
                        url(r'^user/(?P<username>[\w\.]+)/votes/$', 'user_votes', name='app_user_votes'),
                        url(r'^user/(?P<username>[\w\.]+)/votes/(?P<page_index>\d+)/$', 'user_votes', name='app_user_votes'),
                        url(r'^user/(?P<username>[\w\.]+)/comments/$', 'user_comments', name='app_user_comments'),
                        url(r'^user/(?P<username>[\w\.]+)/comments/(?P<page_index>\d+)/$', 'user_comments', name='app_user_comments'),
                        url(r'^user/(?P<username>[\w\.]+)/messages/$', 'user_messages', name='app_user_messages'),
                        url(r'^user/(?P<username>[\w\.]+)/messages/(?P<page_index>\d+)/$', 'user_messages', name='app_user_messages'),
                        url(r'^user/(?P<username>[\w\.]+)/friends/$', 'user_friends', name='app_user_friends'),
                        url(r'^messages/mark/$', 'mark_read', name='app_mark_read'),
                        url(r'^messages/viewed/$', 'mark_viewed', name='app_mark_viewed'),
                        url(r'^search/$', 'search', name='app_search'),
                        url(r'^search/(?P<page_index>\d+)/$', 'search', name='app_search'),
                        url(r'^search/new/$', 'search', {'by_new': True}, name='app_search_new'),
                        url(r'^search/new/(?P<page_index>\d+)/$', 'search', {'by_new': True}, name='app_search_new'),
                        url(r'^search/tag/$', 'tag_search', name='app_tag_search'),
                        url(r'^post/link/$', 'submit_link_post', name='app_link_post'),
                        url(r'^post/text/$', 'submit_text_post', name='app_text_post'),
                        url(r'^p-(?P<post_id>\d+)/$', 'short_url', name='app_post'),
                        url(r'^post/rate/(?P<post_id>\d+)/(?P<slug>[-\w]+)/$', 'rate_post', name='app_post_rate'),
                        url(r'^post/(?P<post_id>\d+)/(?P<slug>[-\w]+)/$', 'read_post', name='app_post'),
                        url(r'^post/pic/(?P<post_id>\d+)/$', 'pic_post', name='app_post_pic'),
                        url(r'^c-(?P<comment_id>\d+)/$', 'short_url', name='app_comment'),
                        url(r'^post/(?P<post_id>\d+)/(?P<slug>[-\w]+)/cid-(?P<comment_id>\d+)/$', 'read_post', name='app_comment'),                                                
                        url(r'^comment/(?P<post_id>\d+)/(?P<slug>[-\w]+)/$', 'comment_save', name='app_comment_save'),
                        url(r'^post/vote/$', 'post_vote', name='app_post_vote'),
                        url(r'^comment/vote/$', 'comment_vote', name='app_comment_vote'),
                        url(r'^reply/(?P<post_id>\d+)/(?P<slug>[-\w]+)/$', 'reply_save', name='app_reply_save'),
                        url(r'^subscribe/$', 'user_subscribe', name='app_subscribe'),
                        url(r'^unsubscribe/$', 'user_unsubscribe', name='app_unsubscribe'),                        
                        url(r'^login/$', 'login', name='app_login'),
                        url(r'^logout/$', 'logout', name='app_logout'),
                        url(r'^signup/$', 'signup', name='app_signup'),
                        url(r'^activation/$', 'activation', name='app_activation'),
                        url(r'^forgot_password/$', 'forgot_password', name='app_forgot_password'),
                        url(r'^change_password/$', 'change_password', name='app_change_password'),
                        url(r'^password_reset/$', 'password_reset', name='app_password_reset'),
                        url(r'^send_activation/$', 'send_activation_code', name='app_send_activation_code'),
                        url(r'^get_title/$', 'get_title', name='app_get_title'),
                        url(r'^mediaplay/(?P<post_id>\d+)/$', 'mediaplay', name='app_mediaplay'),
                        url(r'^facebook_login/$', 'facebook_login', name='app_facebook_login'),
                        url(r'^sitemap.xml$', 'sitemap_xml'),
                        url(r'^\.well-known/host-meta$', TemplateView.as_view(template_name='app/host-meta.xml'), name='app_host_meta'),
                        url(r'^post/oexchange.xrd$', TemplateView.as_view(template_name='app/oexchange.xml'), name='app_oexchange'),
                        url(r'^terms$', 'content_page', {'title':'TangleOn Terms & Conditions', 'content_page':'app/content/terms.md'}, name='app_terms'),
                        url(r'^policy$', 'content_page', {'title':'TangleOn Privacy Policy', 'content_page':'app/content/policy.md'}, name='app_policy'),
                        )


if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^500_page/$', TemplateView.as_view(template_name='500.html')),
        (r'^404_page/$', TemplateView.as_view(template_name='404.html')),
    )
