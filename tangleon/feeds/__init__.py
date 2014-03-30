'''
RSS feeds for all posts
@author: Faraz Masood Khan
'''

from tangleon.app import AnonymousUser
from tangleon.app.models import Channel, Post, Tag

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Rss201rev2Feed
from django.contrib.syndication.views import Feed

MAX_FEEDS = 30

class RssFeedGenerator(Rss201rev2Feed):
    mime_type = u'application/xml'
    
    def root_attributes(self):
        attrs = super(RssFeedGenerator, self).root_attributes()
        attrs['xmlns:media'] = 'http://search.yahoo.com/mrss/'
        return attrs
    
    def add_root_elements(self, handler):
        super(RssFeedGenerator, self).add_root_elements(handler)
        handler.startElement(u'image', {})
        handler.addQuickElement(u"url", u'http://www.tangleon.com/static/app/img/tangleon-logo.png')
        handler.addQuickElement(u"title", u'TangleOn')
        handler.addQuickElement(u"link", u'http://www.tangleon.com/')
        handler.endElement(u'image')
    
    def add_item_elements(self, handler, item):
        super(RssFeedGenerator, self).add_item_elements(handler, item)
        if item['img_url']:
            handler.addQuickElement(u'media:thumbnail', attrs={ u'url': item['img_url']})
        else:
            handler.addQuickElement(u'media:thumbnail', attrs={ u'url': 'http://www.tangleon.com/static/img/tangleon-logo.png'})


class ChannelFeed(Feed):
    feed_type = RssFeedGenerator
    
    def get_object(self, request, channel_id):        
        channel = get_object_or_404(Channel, pk=int(channel_id))
        channel.request = request      
        return channel

    def title(self, channel):
        return u'%s | TangleOn' % channel.title

    def link(self, channel):
        return channel.get_absolute_url()

    def description(self, channel):
        return '%s from tangleon.com news aggregator.' % channel.title

    def items(self, channel):
        feeds = Post.objects.filter(channel=channel, is_muted=False).order_by('-post_id')[:MAX_FEEDS]
              
        for feed in feeds:
            feed.channel_title = channel.title
            yield feed
    
    def item_title(self, feed):
        return feed.title 
    
    def item_description(self, feed):
        return None
    
    def item_link(self, feed):
        return feed.get_absolute_url()
    
    def item_guid(self, feed):
        return 'http://www.tangleon.com' + self.item_link(feed)

    def item_author_name(self, feed):
        return feed.channel_title if feed.channel_title else feed.username
    
    def item_author_link(self, feed):
        return None
     
    def item_pubdate(self, feed):
        return feed.published
    
    def item_categories(self, feed):
        return feed.tags_list()
    
    def item_extra_kwargs(self, feed):
        return {'img_url': feed.img_url }

class AllFeed(ChannelFeed):
    """
    New feeds
    """    
    def get_object(self, request, by_new=False):
        self.request =request
        channel = Channel(channel_id=0, title='Latest Feed' if by_new else 'Top Feed')
        channel.request = request
        channel.by_new = by_new
        return channel
    
    def items(self, channel): 
        return Post.get_posts(0, MAX_FEEDS, channel.by_new, channel.request.app_user, channel.request.GET.get('text_posts', 'true').lower() == 'true')            
    
    def link(self, channel):
        return reverse('app_index_new') if channel.by_new else reverse('app_index')


class TagFeed(ChannelFeed):
    """
    Tag feeds
    """
    def get_object(self, request, tag_name, by_new=False):
        channel = Channel(channel_id=0, title= tag_name)
        channel.request = request
        channel.by_new = by_new
        return channel
    
    def description(self, channel):
        return 'Post of tag %s from tangleon.com aggregator.' % channel.title
        
    def link(self, channel):
        return reverse('app_tag_new', args=[channel.title]) if channel.by_new else reverse('app_tag', args=[channel.title])
    
    def items(self, channel):
        return [post for post in Post.tag_posts(channel.title, 0, 50, channel.by_new, channel.request.app_user) if post.img_url][:30]
    
    

