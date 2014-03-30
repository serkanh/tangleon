"""
Urls for feeds
"""

from django.conf.urls import patterns, include, url

from tangleon.feeds import AllFeed, TagFeed

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^new/$', AllFeed(), {'by_new': True}, name='feeds_new'),
    url(r'^top/$', AllFeed(), name='feeds_top'),
    url(r'^tag/(?P<tag_name>[\w\.@]+)/new/$', TagFeed(), { 'by_new': True }, name='feeds_tag'),
    url(r'^tag/(?P<tag_name>[\w\.@]+)/$', TagFeed(), name='feeds_tag'),
    #url(r'^channel/(?P<channel_id>\d+)/$', ChannelFeeds(), name='feeds_channel'),
    # Examples:
    # url(r'^$', 'tangleon.views.home', name='home'),
    # url(r'^tangleon/', include('tangleon.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
)
