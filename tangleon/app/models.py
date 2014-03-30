"""
Domain models for TangleOn app
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""


import re
import random
import hashlib
import datetime
import thread
import urllib
import feedparser
import HTMLParser
import logging

from django.db.models import F, Q
from django.contrib.sites.models import Site
from django.db import models, connection, transaction
from django.template.defaultfilters import slugify, truncatewords

from tangleon import memoize, settings, TangleOnError
from tangleon.db import models as db_models
from tangleon.app import scraper
from tangleon import rank 

# Get an instance of a logger
logger = logging.getLogger('django.request')
html_parser = HTMLParser.HTMLParser()

_site_url = None
def get_site_url():
    """
    Returns current domain site url
    """
    global _site_url
    if not _site_url:
        _site_url = 'http://' + Site.objects.get_current().domain
        
    return _site_url


class User(models.Model):
    """
    TangleOn user to subscribing channels or pinning tags and making comments
    """   
    user_id = db_models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    post_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    follower_count = models.IntegerField(default=0)
    up_votes = models.IntegerField(default=0)
    down_votes = models.IntegerField(default=0)
    has_activated = models.BooleanField(default=False)    
    activation_code = models.CharField(max_length=512)
    activation_code_expiry = models.DateTimeField()
    last_logged_in = models.DateTimeField(blank=True, null=True)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=75)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    def __str__(self):
        return str(self.username)
    
    def __unicode__(self):
        return unicode(self.username)
    
    @memoize.method
    @models.permalink
    def get_absolute_url(self):
        """
        Returns absolute url of user posts
        """        
        return ('app_user', (self.username,))

    def is_authenticated(self):
        """
        Returns true for authenticated user
        """
        return True     
    
    def is_anonymous(self):
        """        
        Returns true of anonymous user
        """
        return False
    
    def is_admin(self):
        """
        Returns true if email address of user specified as tangleon admin in settings ADMIN_EMAILS
        """
        return self.email in settings.ADMIN_EMAILS
     
    def get_and_delete_messages(self):
        """
        Dummy function to replicate django admin users behavior
        """
        return []
    
    def get_flash_messages(self):
        """
        Returns user flash messages and delete them in database
        """
        return FlashMessage.get_messages(self)
    
    def peek_flash_messages(self):
        """
        Returns user flash messages and don't delete them in database
        """
        return FlashMessage.peek_messages(self)
    
    def login(self):
        """
        Sets last_logged_in time of user in database
        """
        now = datetime.datetime.now()
        self.last_logged_in = now
        self.updated_on = now
        self.updated_by = str(self.user_id)
        self.save()
        
    def get_posts(self, page_index, page_size, sort_by_new, user):
        """
        Returns posts submitted by user
        """
        return Post.user_posts(self, page_index, page_size, sort_by_new, user)
            
    def get_by_comments(self, page_index, page_size, login_user):
        """
        Returns posts on which user made any comments
        """
        return Post.comment_posts(self, page_index, page_size, login_user)

    def get_by_messages(self, page_index, page_size, login_user):
        """
        Returns posts on which user made any comments
        """
        return Post.messages_posts(self, page_index, page_size, login_user)

    def get_by_votes(self, page_index, page_size, login_user):
        """
        Returns posts on which user voted
        """
        return Post.vote_posts(self, page_index, page_size, login_user)
    
    def last_post(self):
        """
        Returns last post of the user
        """        
        posts = self.post_set.filter(is_muted=False).order_by('-post_id')[0:1]
        return posts[0] if posts else None 
    
    def get_followings(self):
        """
        Returns list of following users        
        """
        return Follow.get_followings(self)
        
    def get_channels(self):
        """
        Returns list of user's subscribed channels
        """
        return Subscription.get_channels(self)
    
    def get_tags(self):
        """
        Returns list of user's pinned tags
        """
        return Pin.get_tags(self)
    
    def get_messages(self):
        """
        Returns user messages
        """
        return Message.get_messages(self)
        
    @classmethod 
    def sign_up(cls, username, email, password):
        """
        Creates a new non-admin user in database 
        """
        activation_code = Credential.random_digest()
        password_hash = Credential.password_hexdigest(password=password)
        username = username.lower()
        email = email.lower()
        with transaction.commit_on_success():
            try:
                user = cls.objects.get(Q(username=username) | Q(email=email))
                error_message = 'Username "%s" already registered with us, if you forgot your password? <a href="/forgot_password/">Request new one</a> or choose a different username.' % username if user.username == username else 'Its seems to be that you are already registered with this email address, if you forgot your password? <a href="/forgot_password/">Request new one.</a>'
                raise TangleOnError(error_message)
            except cls.DoesNotExist:                            	            	
                user, created = cls.objects.get_or_create(username=username,
                                                           email=email,
                                                           activation_code=activation_code,
                                                           activation_code_expiry=datetime.datetime.now() + datetime.timedelta(days=2),
                                                           updated_by=email,
                                                           created_by=email)
                if not created:
                    raise TangleOnError('It is seems to be that you are already registered with this email address, if you forgot your password? <a href="/forgot_password/">Request new one.</a>')
                
                user.save()                
                credential = Credential(user=user, password_hash=password_hash, updated_by=email)
                credential.save()
                
                # Subscribing all default channels                
                for channel in Channel.objects.filter(is_muted=False, is_default=True):
                    Channel.objects.filter(channel_id=channel.channel_id).update(subscription_count=F('subscription_count') + 1)                    
                    Subscription.objects.create(user=user, channel=channel, created_by=email)
                                
                
                # Pining all default tags
                for tag in Tag.objects.filter(is_muted=False, is_default=True):
                    Tag.objects.filter(tag_id=tag.tag_id).update(pin_count=F('pin_count') + 1)
                    Pin.objects.create(user=user, tag=tag, created_by=email)
                
                return user
    
    @classmethod
    def activate(cls, email, activation_code):
        """
        Activates a non-admin user
        """
        email = email.lower()
        try:
            user = cls.objects.get(email=email)
            if user.activation_code == activation_code:
                if user.has_activated:
                    raise TangleOnError('Your account is already activated, please <a href="/login/">login</a> here.')
                
                if user.activation_code_expiry < datetime.datetime.now():
                    raise TangleOnError('Your account activation code is expired!, please click <a href="/send_activation/?email=%s">here</a> to re-send activation code.' % email)
                
                user.has_activated = True
                user.updated_by = email
                user.save()
                return user                
            else:
                raise TangleOnError('Your account activation code is invalid.')
        except cls.DoesNotExist:
            raise TangleOnError('Your are not registered with us, please click <a href="/signup/">here</a> to sign up.')        
     
    @classmethod
    def generate_activation_code(cls, email):
        """
        Generate new activation code for the user
        """
        email = email.lower()
        try:
            user = cls.objects.get(email=email)
            if user.has_activated:
                raise TangleOnError('Your account is already activated.')
                
            user.activation_code = Credential.random_digest()
            user.activation_code_expiry = datetime.datetime.now() + datetime.timedelta(days=2)
            user.updated_by = email
            user.save()
            return user
           
        except cls.DoesNotExist:
            raise TangleOnError('Your are not registered with us, please click <a href="/signup/">here</a> to sign up.')        


class Credential(models.Model):    
    user = models.ForeignKey(User, primary_key=True)
    password_hash = models.CharField(max_length=512)
    reset_code = models.CharField(max_length=512, blank=True, null=True)
    reset_code_expiry = models.DateTimeField(blank=True, null=True)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=75)    
    
    @classmethod
    def password_hexdigest(cls, salt=None, password=''):
        if salt is None:
            salt = random.randint(1000, 10000)       
        return '%s$%s' % (salt, cls.hexdigest(password))
    
    @classmethod
    def authenticate(cls, username, password):
        username = username.lower()
        try:
            user = User.objects.get(email=username) if '@' in username else User.objects.get(username=username) 
            try:
                credential = cls.objects.get(user=user)            
                salt = credential.password_hash.split('$')[0]
                if credential.password_hash == cls.password_hexdigest(salt, password):
                    return user
            except cls.DoesNotExist:
                pass
        except User.DoesNotExist:
            pass         
    
    @classmethod
    def change_password(cls, user, password, new_password):        
        credential = cls.objects.get(user_id=user.user_id)        
        salt = credential.password_hash.split('$')[0]
        if credential.password_hash == cls.password_hexdigest(salt, password):
            credential.password_hash = cls.password_hexdigest(salt, new_password)              
            credential.updated_by = str(user)
            credential.save()
        else:
            raise TangleOnError('Wrong password! please enter your current password again.')
    
    @classmethod
    def generate_reset_code(cls, email):
        email = email.lower()
        try:
            user = User.objects.get(email=email)            
            credential = Credential.objects.get(user=user)
            credential.reset_code = cls.random_digest()
            credential.reset_code_expiry = datetime.datetime.now() + datetime.timedelta(days=1)
            credential.updated_by = str(user)
            credential.save()
            return user, credential
        
        except User.DoesNotExist:
            raise TangleOnError('Your email address doesn''t exist, would you like to <a href="/signup/">sign up</a>?')
    
    @classmethod
    def password_reset(cls, email, reset_code, password):
        email = email.lower()
        try:
            user = User.objects.get(email=email)
            credential = user.credential_set.all()[0]
            if credential.reset_code == reset_code:
                now = datetime.datetime.now()
                if credential.reset_code_expiry < now:
                    raise TangleOnError('This reset code is expired, please obtain a new one.')
                credential.password_hash = cls.password_hexdigest(password=password)                
                credential.updated_by = email
                credential.reset_code_expiry = now
                credential.save()
            else:
                raise TangleOnError('Reset code is invalid.')        
        except User.DoesNotExist:
            raise TangleOnError('Email address is not registered with us.')
    
    @classmethod
    def random_digest(cls):
        return cls.hexdigest(str(random.randrange(100, 10000000)))
   
    @staticmethod
    def hexdigest(value):
        algo = hashlib.md5()
        algo.update(value)
        return algo.hexdigest() 


class Follow(models.Model):
    """
    User following class
    """
    follow_id = db_models.BigAutoField(primary_key=True)
    follower = models.ForeignKey(User, related_name='follower')
    following = models.ForeignKey(User, related_name='following')
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    class Meta:
        unique_together = ('follower', 'following')
    
    @classmethod
    def get_followings(cls, follower):
        """
        Returns list of users followed by this user
        """
        return [user for user in User.objects.raw('''
                                               SELECT u.*, fb.name AS fb_name, fb.fb_id AS fb_id
                                               FROM app_user u
                                               INNER JOIN app_follow f ON u.user_id = f.following_id AND f.follower_id = %s
                                               LEFT OUTER JOIN app_fbuser fb ON u.user_id = fb.user_id
                                               ORDER BY f.follow_id
                                               ''', [follower.user_id])]
    
    @classmethod
    def follow(cls, username, follower):
        """
        Start following user
        """
        following = User.objects.get(username__iexact=username)
        if not cls.objects.filter(following=following, follower=follower).exists() and following.user_id != follower.user_id:
            cls.objects.create(following=following, follower=follower)
            User.objects.filter(user_id=following.user_id).update(follower_count=F('follower_count') + 1)
    
    @classmethod
    def unfollow(cls, username, follower):
        """
        Unfollow the user
        """
        try:
            following = User.objects.get(username__iexact=username)
            follow = cls.objects.get(following=following, follower=follower)
            follow.delete()
            User.objects.filter(user_id=following.user_id).update(follower_count=F('follower_count') - 1)
        except cls.DoesNotExist:
            pass        
     

class Channel(models.Model):
    """
    Channel class for RSS feeds sources
    """    
    channel_id = models.AutoField(primary_key=True)
    url = models.URLField(unique=True)
    link = models.URLField()
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True, null=True)
    icon_url = models.URLField(blank=True, null=True)
    is_default = models.BooleanField()
    is_muted = models.BooleanField(default=False)
    sync_on = models.DateTimeField()        
    published = models.DateTimeField()
    subscription_count = models.IntegerField(default=0)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=75)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    sync_lock = thread.allocate_lock()
    sync_channel_ids = []
    
    def __unicode__(self):
        return unicode(self.title)   
    
    def get_posts(self, page_index, page_size, sort_by_new, user):
        '''Returns all posts of the channel'''
        
        return Post.channel_posts(self, page_index, page_size, sort_by_new, user)
    
    @models.permalink
    def get_absolute_url(self):
        """
        Returns channel absolute url
        """       
        return ('app_channel', (self.channel_id,))
    
    def sync(self, user, forced=None):
        now = datetime.datetime.now()        
        if not self.is_muted and self.subscription_count and (forced or self.sync_on < (now - datetime.timedelta(minutes=60))):
            with Channel.sync_lock:
                if self.channel_id in Channel.sync_channel_ids:
                    return
                Channel.sync_channel_ids.append(self.channel_id)
                
            thread.start_new_thread(self.sync_channel, (user,))                   
    
    def sync_channel(self, user):
        now = datetime.datetime.now()
        try:                   
            channel = Channel.objects.get(channel_id=self.channel_id)            
            try:
                rss = feedparser.parse(self.url)
            except Exception:
                raise TangleOnError('Error occurred while curling for RSS post.')
                        
            if not channel.description or not channel.icon_url:
                icon_url, description = scraper.get_icon_url_and_description(rss.feed.link, rss.feed)
                channel.description = description
                channel.icon_url = icon_url
                Channel.objects.filter(channel_id=self.channel_id).update(published=Post.get_date(rss.feed, now),
                                                                          sync_on=now,
                                                                          updated_by=str(user),
                                                                          description=description,
                                                                          icon_url=icon_url)
            else:
                Channel.objects.filter(channel_id=self.channel_id).update(published=Post.get_date(rss.feed, now),
                                                                          sync_on=now,
                                                                          updated_by=str(user))
                        
            for entry in rss.entries:
                try:
                    guid = hash(channel.url + '#' + entry.link)
                    title = html_parser.unescape(entry.title)
                    if not Post.objects.filter(Q(guid=guid) | Q(title=title)).exists():
                        post = Post.from_entry(channel, now, user, entry)
                        post.save()
                except TangleOnError: pass
                except Exception as e: logger.exception(e)                
        finally:            
            with Channel.sync_lock:
                if self.channel_id in Channel.sync_channel_ids:
                    Channel.sync_channel_ids.remove(self.channel_id)     
        
    @classmethod
    def subscribe(cls, url, user):
        if url.startswith('http://www.tangleon.com') or url.startswith('https://www.tangleon.com'):
            raise TangleOnError('Recursive post subscription loop detected.')
        
        try:
            channel = Channel.objects.get(url=url)
        except Channel.DoesNotExist:
            channel = Channel.add_channel(url, user)
                        
        try:
            subscription = Subscription.objects.get(user=user, channel=channel)
            raise TangleOnError('You are already subscribe to this post.')
        except Subscription.DoesNotExist:
            subscription = Subscription.objects.create(user=user,
                                                       channel=channel,
                                                       created_by=str(user))
            subscription.save()
        return channel

    @classmethod
    def top_channels(cls, max_channels=10):
        return [channel for channel in cls.objects.filter(is_muted=False, subscription_count__gt=2).order_by('-subscription_count')[:max_channels]]

    @classmethod
    def add_channel(cls, url, user):        
        try:
            rss = feedparser.parse(url)
        except Exception:
            raise TangleOnError('Error occurred while curling for RSS post.')
        
        feed = rss.feed
        now = datetime.datetime.now()
        icon_url, description = scraper.get_icon_url_and_description(feed.link, feed)
        channel = Channel(url=url,
                          title=feed.title,
                          link=feed.link,
                          icon_url=icon_url,
                          description=description,
                          published=Post.get_date(feed, now),
                          sync_on=now,
                          updated_by=str(user),
                          created_by=str(user))
        
        channel.save()
        
        if not channel.title:
            channel.title = 'RSS Channel ' + str(channel.channel_id)
            channel.save()
        
        for entry in rss.entries:
            post = Post.from_entry(channel, now, user, entry)
            post.save()
        return channel
    
    @classmethod
    def get_channels(cls):
        return list(cls.objects.filter(is_muted=False, is_default=True).order_by('channel_id'))


class Post(models.Model):
    """
    Post class for all posts from channel or user
    """
    post_id = db_models.BigAutoField(primary_key=True)
    channel = models.ForeignKey(Channel, null=True, blank=True)
    user = models.ForeignKey(User, null=True, blank=True)    
    guid = models.BigIntegerField()
    title = models.TextField(db_index=True)
    description = models.TextField(null=True, blank=True)
    slug = models.SlugField(max_length=256)
    link = models.URLField(max_length=1024)
    img_url = models.URLField(null=True, blank=True, max_length=1024)
    img_alt = models.CharField(null=True, blank=True, max_length=256)
    vid_url = models.URLField(null=True, blank=True, max_length=1024)
    vid_type = models.CharField(null=True, blank=True, max_length=50)
    author = models.CharField(max_length=256, blank=True, null=True)
    published = models.DateTimeField()
    votes = models.IntegerField(default=0)
    up_votes = models.IntegerField(default=0)
    down_votes = models.IntegerField(default=0)
    rank = models.FloatField(default=0, db_index=True)
    tags = models.TextField(null=True, blank=True, db_index=True)
    comment_count = models.IntegerField(default=0)
    is_muted = models.BooleanField(default=0)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=75)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    class Meta:
        unique_together = ('channel', 'user', 'link')
    
    @property
    def likes_percentage(self):
        """
        Returns percentage of likes votes in total votes
        """
        total_votes = self.up_votes + self.down_votes
        return int(self.up_votes * 100 / (total_votes)) if total_votes else 0
    
    @property
    def scaled_rating(self):
        """
        Base on like votes and confidence caculate rating from 1 - 5
        """
        # Google accept rating from 1 - 5 therefore flooring value to 1
        return max(self.rating() * 5, 1.0)        
        
    def rating(self):
        """
        Returns confidence on post based on number of votes using Wilson's score interval
        """
        return round(rank.rating(self.up_votes, self.down_votes), 1)
    
    def is_text_post(self):
        """
        Returns true if it is text post        
        """
        return self.link.startswith('http://www.tangleon.com')
        
    @property
    @memoize.method
    def preview_img_url(self):
        """
        Returns scaled image url for preview
        """
        if self.img_url:
            if self.img_url.startswith('http://'):
                preview_img_url = self.img_url[7:]
            elif self.img_url.startswith('https://'):
                preview_img_url = 'ssl:' +  self.img_url[8:]
            elif self.img_url.startswith('//'):
                preview_img_url = self.img_url[2:]
            else:
                preview_img_url = self.img_url
                    
            return u'http://images.weserv.nl/?' + urllib.urlencode({'url': unicode(preview_img_url).encode('utf-8'), 'w':600, 'h':450, 't': 'square'})
        
        return None
        
    
    def __unicode__(self):
        return unicode(self.title)       
    
    @memoize.method     
    def tags_list(self):
        """
        Returns limited list of tags 
        """        
        return [tag for tag in self.tags.split(',') if len(tag) > 2][:5]
    
    @memoize.method
    @models.permalink
    def get_absolute_url(self):
        """
        Returns absolute url of this post
        """
        return ('app_post', (self.post_id, self.slug,))
    
    @memoize.method
    @models.permalink
    def get_short_url(self):
        """
        Returns posts url post_id only
        """
        return ('app_post', (self.post_id,))
    
    @classmethod
    def submit_post(cls, user, title, tags, url=None, description=None):
        """
        Saves a new post in database
        """
        now = datetime.datetime.now()
        tags = ('' + tags).strip(', ')
        media_tags = scraper.get_media_tags(url) if url else {}    
                    
        post = cls.objects.create(guid=0,
                                  user=user,
                                  title=html_parser.unescape(title),
                                  link=(url if url else 'http://www.tangleon.com')[:1024],
                                  slug=slugify(truncatewords(title, 10)),
                                  description=description,
                                  published=now,
                                  img_url=media_tags.get('image', '')[:1024],
                                  img_alt=title[:256] if 'image' in media_tags else None,
                                  vid_url=media_tags.get('video', '')[:1024],
                                  vid_type=media_tags.get('video_type', ''),
                                  author=str(user),
                                  tags=tags,
                                  updated_by=str(user),
                                  created_by=str(user))
        
        post.link = url if url else get_site_url() + post.get_absolute_url()
        post.guid = hash(str(user) + '#' + post.link)
        post.save()
        
        # Creating new tags
        Tag.add_tags(tags.split(','), user)
        
        # Updating post count in user
        User.objects.filter(user_id=user.user_id).update(post_count=F('post_count') + 1)
        
        return post
        
    @classmethod
    def read_post(cls, post_id, slug, user, comment_id=None, max_comments=20):
        """
        Returns post with all it's comments sorted
        """
        result = list(cls.objects.raw('''
                                      SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index
                                      FROM app_post p
                                      LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
                                      LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
                                      LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                                      WHERE p.post_id = %s AND p.slug = %s
                                      ''', [user.user_id, post_id, slug]))
        
        if len(result) == 0:
            raise Post.DoesNotExist
        
        post = result[0]
        
        if not post.is_muted and max_comments:
            if comment_id:            
                comments = list(Comment.objects.raw('''
                                                    SELECT c.*, v.vote AS vote_index
                                                    FROM app_comment c
                                                    LEFT OUTER JOIN app_commentvote v ON c.comment_id = v.comment_id AND v.user_id = %s
                                                    WHERE c.post_id = %s AND c.comment_id >= %s 
                                                    ORDER BY c.rank DESC, c.comment_id
                                                    LIMIT %s
                                                    ''', [user.user_id, post_id, comment_id, max_comments]))
            else:
                comments = list(Comment.objects.raw('''
                                                    SELECT c.*, v.vote AS vote_index
                                                    FROM app_comment c
                                                    LEFT OUTER JOIN app_commentvote v ON c.comment_id = v.comment_id AND v.user_id = %s
                                                    WHERE c.post_id = %s
                                                    ORDER BY c.rank DESC, c.comment_id
                                                    LIMIT %s
                                                    ''', [user.user_id, post_id, max_comments]))                   
            
            post.loaded_comments = comments
            if comment_id:
                post.comments = [comment for comment in comments if comment.comment_id == comment_id]
            else:
                post.comments = [comment for comment in comments if comment.reply_to_id == None]
            
            
            for comment in comments:
                comment.post = post
                comment.replies = [reply for reply in comments if reply.reply_to_id == comment.comment_id]
        
        return post
        
    @classmethod
    def get_posts(cls, page_index, page_size, sort_by_new, user, text_posts=True):
        """
        Returns posts from all sources and user
        """                
        if sort_by_new:
            sql_query = '''
                        SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index
                        FROM app_post p
                        LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
                        LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.is_muted = False AND (%s OR p.img_url IS NOT NULL)
                        ORDER BY p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
        else:
            sql_query = '''
                        SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index
                        FROM app_post p
                        LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
                        LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.is_muted = False AND (%s OR p.img_url IS NOT NULL)
                        ORDER BY p.rank DESC, p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
        
        return [post for post in cls.objects.raw(sql_query, [user.user_id, text_posts, page_size, page_index * page_size])]
    
    @classmethod
    def channel_posts(cls, channel, page_index, page_size, sort_by_new, user):
        """
        Returns post from particular channel
        """
        if sort_by_new:
            sql_query = '''
                        SELECT p.*, c.title AS channel_title, c.link AS channel_link, NULL AS username, v.vote AS vote_index
                        FROM app_post p
                        LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id                        
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.channel_id = %s AND p.is_muted = False
                        ORDER BY p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
        else:
            sql_query = '''
                        SELECT p.*, c.title AS channel_title, c.link AS channel_link, NULL AS username, v.vote AS vote_index
                        FROM app_post p
                        LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id                        
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.channel_id = %s AND p.is_muted = False
                        ORDER BY p.rank DESC, p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
            
        return [post for post in cls.objects.raw(sql_query, [user.user_id, channel.channel_id, page_size, page_index * page_size])]
    
    @classmethod
    def user_posts(cls, user, page_index, page_size, sort_by_new, login_user):
        """
        Return posts of particular user
        """
        if sort_by_new:
            sql_query = '''
                        SELECT p.*, NULL AS channel_title, NULL AS channel_link, u.username, v.vote AS vote_index
                        FROM app_post p                        
                        LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.user_id = %s AND p.is_muted = False
                        ORDER BY p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
        else:
            sql_query = '''
                        SELECT p.*, NULL AS channel_title, NULL AS channel_link, u.username, v.vote AS vote_index
                        FROM app_post p                        
                        LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.user_id = %s AND p.is_muted = False
                        ORDER BY p.rank DESC, p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
            
        return [post for post in cls.objects.raw(sql_query, [login_user.user_id, user.user_id, page_size, page_index * page_size])]
    
    @classmethod
    def users_posts(cls, page_index, page_size, sort_by_new=False):
        """
        Return posts of particular user
        """
        posts = Post.objects.filter(channel_id__exact=None, is_muted=False)
        
        if sort_by_new:
            return [post for post in posts.order_by('-post_id')[page_index * page_size:(page_index + 1) * page_size]]
        
        return [post for post in posts.order_by('-rank', '-post_id')[page_index * page_size:(page_index + 1) * page_size]]
    
    @classmethod
    def comment_posts(cls, user, page_index, page_size, login_user):
        """
        Returns posts on which user made any comments
        """
        sql_query = '''
            SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index, uc.comment_id, uc.comment_text, uc.created_on AS comment_date
            FROM app_post p
            INNER JOIN app_comment uc ON p.post_id = uc.post_id AND uc.user_id = %s AND uc.is_muted = False AND p.is_muted = False
            LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
            LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
            LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s            
            ORDER BY uc.comment_id DESC
            LIMIT %s OFFSET %s
            '''
        
        return [post for post in cls.objects.raw(sql_query, [user.user_id, login_user.user_id, page_size, page_index * page_size])]

    @classmethod
    def messages_posts(cls, user, page_index, page_size, login_user):
        """
        Returns posts on which user has been commented to replied for any comment
        """
        sql_query = '''
            SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index, ur.comment_id, ur.comment_text, ur.created_by AS comment_by, ur.created_on AS comment_date
            FROM app_post p
            INNER JOIN app_comment ur ON p.post_id = ur.post_id AND ur.is_muted = False AND p.is_muted = False
            LEFT OUTER JOIN app_comment uc ON uc.comment_id = ur.reply_to_id AND uc.user_id = %s AND ur.user_id != %s
            LEFT OUTER JOIN app_post up ON ur.post_id = up.post_id AND up.user_id = %s AND ur.user_id != %s AND ur.reply_to_id is null
            LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
            LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
            LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
            WHERE uc.user_id IS NOT NULL or up.user_id  IS NOT NULL
            ORDER BY ur.comment_id DESC
            LIMIT %s OFFSET %s
            '''
        
        return [post for post in cls.objects.raw(sql_query, [user.user_id, user.user_id, user.user_id, user.user_id, login_user.user_id, page_size, page_index * page_size])]
        
    @classmethod
    def vote_posts(cls, user, page_index, page_size, login_user):
        """
        Returns posts on which user voted
        """
        sql_query = '''
            SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index
            FROM app_post p
            INNER JOIN app_postvote uv ON p.post_id = uv.post_id
            LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
            LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
            LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
            WHERE uv.user_id = %s AND uv.vote <> 0 AND p.is_muted = False
            ORDER BY uv.vote_id DESC
            LIMIT %s OFFSET %s
            '''
        
        return [post for post in cls.objects.raw(sql_query, [login_user.user_id, user.user_id, page_size, page_index * page_size])]
    
    @classmethod
    def tag_posts(cls, tag, page_index, page_size, sort_by_new, user):
        """
        Returns post of related tag found in title or tags field
        """        
        tag = '%' + tag + '%'
        
        if sort_by_new:
            sql_query = '''
                        SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index
                        FROM app_post p
                        LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
                        LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.is_muted = False AND (p.title ILIKE %s OR p.tags ILIKE %s OR c.title ILIKE %s)
                        ORDER BY p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
        else:
            sql_query = '''
                        SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index
                        FROM app_post p
                        LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
                        LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.is_muted = False AND (p.title ILIKE %s OR p.tags ILIKE %s OR c.title ILIKE %s)
                        ORDER BY p.rank DESC, p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
        
        return [post for post in cls.objects.raw(sql_query, [user.user_id, tag, tag, tag, page_size, page_index * page_size])]  

    @classmethod
    def room_posts(cls, room, page_index, page_size, sort_by_new, user):
        """
        Returns post of related room found in first tag of tags field
        """
        if sort_by_new:
            sql_query = '''
                        SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index
                        FROM app_post p
                        LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
                        LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.is_muted = False AND (lower(p.tags) = lower(%s) OR p.tags ILIKE %s)
                        ORDER BY p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
        else:
            sql_query = '''
                        SELECT p.*, c.title AS channel_title, c.link AS channel_link, u.username, v.vote AS vote_index
                        FROM app_post p
                        LEFT OUTER JOIN app_channel c ON p.channel_id = c.channel_id
                        LEFT OUTER JOIN app_user u ON p.user_id = u.user_id
                        LEFT OUTER JOIN app_postvote v ON p.post_id = v.post_id AND v.user_id = %s
                        WHERE p.is_muted = False AND (lower(p.tags) = lower(%s) OR p.tags ILIKE %s)
                        ORDER BY p.rank DESC, p.post_id DESC
                        LIMIT %s OFFSET %s
                        '''
        
        return [post for post in cls.objects.raw(sql_query, [user.user_id, room, (room + ',%'), page_size, page_index * page_size])]
   
    @classmethod
    def from_entry(cls, channel, now, user, entry):
        """
        Creates Post object from entry object of RSS
        """
        tags = Tag.clean_tags(tag.term for tag in entry.tags) if 'tags' in entry else ''  
        author = entry.author_detail.name if 'author_detail' in entry else ''
        
        # Trying to get media info from post page
        media_tags = scraper.get_media_tags(entry.link)
            
        # Getting first image url from RSS item description
        if not 'image' in media_tags:
            media_tags['image'] = scraper.get_img_url_from_entry(entry)
            media_tags['image_alt'] = scraper.get_img_alt_from_entry(entry) if media_tags['image'] else ''
        else:
            media_tags['image_alt'] = entry.title
            
        img_url = media_tags.get('image', None)
        img_alt = media_tags.get('image_alt', None)
        vid_url = media_tags.get('video', None)
        vid_type = media_tags.get('video_type', None)
        return cls(channel=channel,
                   guid=hash(channel.url + '#' + entry.link),
                   title=html_parser.unescape(entry.title),
                   link=entry.link[:1024],
                   slug=slugify(truncatewords(entry.title, 10)),
                   published=cls.get_date(entry, now),
                   img_url=img_url[:1024] if img_url else None,
                   img_alt=img_alt[:256] if img_alt else None,
                   vid_url=vid_url[:1024] if vid_url else None,
                   vid_type=vid_type,
                   author=author,
                   tags=tags,
                   rank=-999, # Ranking will be calculated with cron job 
                   updated_by=str(user),
                   created_by=str(user))
    
    @staticmethod
    def get_date(post_or_entry, default):
        if 'published_parsed' in post_or_entry:
            return datetime.datetime(*post_or_entry.published_parsed[:6])
        
        return default
    
    @staticmethod
    def get_cut_off():
        return datetime.datetime.now() - datetime.timedelta(days=30)

        
class Tag(models.Model):
    tag_id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=50)
    description = models.TextField(blank=True, null=True)
    is_muted = models.BooleanField(default=False)
    pin_count = models.IntegerField(default=0)
    is_default = models.BooleanField(default=False)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=75)
    
    @models.permalink
    def get_absolute_url(self):
        """
        Returns absolute tag url
        """
        return ('app_tag', (self.name,))
    
    def __unicode__(self):
        return unicode(self.name)
    
    @classmethod
    def add_tags(cls, tags, user):
        """
        Create new tags in database if doesn't exists
        """        
        sql = '''INSERT INTO app_tag (name, is_muted, is_default, pin_count, updated_by, updated_on) 
                 SELECT %s, false, false, 0, %s, %s WHERE NOT EXISTS (SELECT 1 FROM app_tag WHERE lower(name) = lower(%s));'''
        now = datetime.datetime.now()
        parameters = ((tag, str(user), now, tag) for tag in tags)
        cursor = connection.cursor()
        try:
            cursor.executemany(sql, parameters)
        finally:
            cursor.close()
        
    
    @classmethod
    def get_tags(cls):
        return [tag for tag in cls.objects.filter(is_muted=False, is_default=True).order_by('tag_id')]
    
    @classmethod
    def top_tags(cls, max_tags=10):
        return [tag for tag in cls.objects.filter(is_muted=False, pin_count__gt=2).order_by('-pin_count')[:max_tags]]
    
    @staticmethod
    def clean_tags(tags):
        """
        Return cleaned tags string, removed spaces and special characters
        """
        tags = (re.sub(r'[^\w\.@]', '', tag) for tag in tags) 
        tags = ','.join(tag for tag in tags if len(tag) > 1 and len(tag) <= 20)
        return tags


class Subscription(models.Model):
    subscription_id = db_models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    channel = models.ForeignKey(Channel)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    @classmethod
    def subscribe(cls, channel_id, user):
        
        if cls.objects.filter(channel_id=channel_id, user=user).count() == 0:
            cls.objects.create(channel_id=channel_id, user=user, created_by=str(user))
            Channel.objects.filter(channel_id=channel_id).update(subscription_count=F('subscription_count') + 1)
    
    @classmethod
    def unsubscribe(cls, channel_id, user):        
        try:
            subscription = cls.objects.get(channel_id=channel_id, user=user)
            subscription.delete()
            Channel.objects.filter(channel_id=channel_id).update(subscription_count=F('subscription_count') - 1)
        except cls.DoesNotExist:
            pass
    
    @staticmethod
    def get_channels(user):
        return [channel for channel in Channel.objects.raw('''
                                                           SELECT c.*
                                                           FROM app_subscription s
                                                           INNER JOIN app_channel c on s.channel_id = c.channel_id
                                                           WHERE c.is_muted = false AND s.user_id = %s
                                                           ORDER BY s.subscription_id
                                                           ''', [user.user_id])]   
    


class Pin(models.Model):
    pin_id = db_models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    tag = models.ForeignKey(Tag)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)        
        
    @classmethod
    def pin_tag(cls, tag_name, user):
        """
        Pin tag to user profile
        """        
        # Due to case sensitive name of tag.name field, double checking tag creation
        tag_name = tag_name.strip()
        try:
            tag = Tag.objects.get(name__iexact=tag_name)
        except Tag.DoesNotExist:
            tag, created = Tag.objects.get_or_create(name=tag_name, updated_by=str(user))
        
        if not cls.objects.filter(tag=tag, user=user).exists():
            cls.objects.create(tag=tag, user=user, created_by=str(user))
            Tag.objects.filter(tag_id=tag.tag_id).update(pin_count=F('pin_count') + 1)
    
    @classmethod
    def unpin_tag(cls, tag_name, user):
        tag_name = tag_name.strip()
        try:
            pin_tag = cls.objects.get(tag__name__iexact=tag_name, user=user)
            pin_tag.delete()
            Tag.objects.filter(name__iexact=tag_name).update(pin_count=F('pin_count') - 1)
        except cls.DoesNotExist:
            pass             
    
    @staticmethod
    def get_tags(user):
        return [tag for tag in Tag.objects.raw('''
                                               SELECT t.*
                                               FROM app_pin p
                                               INNER JOIN app_tag t on p.tag_id = t.tag_id
                                               WHERE t.is_muted = false AND p.user_id = %s
                                               ORDER BY p.pin_id
                                               ''', [user.user_id])]


class Comment(models.Model):
    """
    User comments for each post
    """
    comment_id = db_models.BigAutoField(primary_key=True)
    post = models.ForeignKey(Post)
    reply_to = models.ForeignKey('self', null=True, blank=True)
    user = models.ForeignKey(User)
    comment_text = models.TextField()
    votes = models.IntegerField(default=0)
    up_votes = models.IntegerField(default=0)
    down_votes = models.IntegerField(default=0)
    rank = models.FloatField(default=0, db_index=True)
    reply_count = models.IntegerField(default=0)
    is_muted = models.BooleanField(default=0)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    def __unicode__(self):
        return self.comment_text[:50]
    
    @memoize.method
    @models.permalink
    def get_short_url(self):
        """
        Returns short url of the comment, which will redirect to completed url
        """
        return ('app_comment', (self.post_id, self.post.slug, self.comment_id,))
    
    @memoize.method
    @models.permalink
    def get_absolute_url(self):
        """
        Returns absolute url of the comment
        """
        return ('app_comment', (self.post_id, self.post.slug, self.comment_id,))
    
    @classmethod
    def save_comment(cls, user, post_id, slug, comment_text):
        """
        Save user comments for the post in database
        """
        if Post.objects.filter(post_id=post_id, slug=slug).update(comment_count=F('comment_count') + 1) == 1:
            User.objects.filter(user_id=user.user_id).update(comment_count=F('comment_count') + 1)
            comment = cls.objects.create(post_id=post_id, user=user, comment_text=comment_text, created_by=str(user))
            Message.add_comment_msg(comment, user)
            return comment

    @classmethod
    def save_reply(cls, user, post_id, slug, comment_id, comment_text):
        """
        Save user comments for the post in database
        """
        if Post.objects.filter(post_id=post_id, slug=slug).update(comment_count=F('comment_count') + 1) == 1:
            User.objects.filter(user_id=user.user_id).update(comment_count=F('comment_count') + 1)
            cls.objects.filter(comment_id=comment_id).update(reply_count=F('reply_count') + 1)
            comment = cls.objects.create(post_id=post_id, reply_to_id=comment_id, user=user, comment_text=comment_text, created_by=str(user))
            Message.add_reply_msg(comment, user)
            return comment



class PostVote(models.Model):
    """
    Keep track of user vote on post
    """
    vote_id = db_models.BigAutoField(primary_key=True)
    post = models.ForeignKey(Post)
    user = models.ForeignKey(User)
    vote = models.IntegerField(default=0)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=75)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    class Meta:
        unique_together = ('post', 'user',)
    
    @classmethod
    def up_vote(cls, user, post_id):
        """
        Vote up if user not voted otherwise makes it zero
        """
        try:
            post_vote = cls.objects.get(post_id=post_id, user_id=user.user_id)
        except PostVote.DoesNotExist:
            post_vote = cls.objects.create(post_id=post_id, user_id=user.user_id, updated_by=str(user), created_by=str(user))
        
        cursor = connection.cursor()
        try:
                  
            if post_vote.vote == 0:
                cls.objects.filter(post_id=post_id, user_id=user.user_id).update(vote=1, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(up_votes=F('up_votes') + 1)
                cursor.execute('''UPDATE app_post SET up_votes = up_votes + 1, votes = (up_votes - down_votes + 1), rank = compute_rank(up_votes - down_votes + 1, created_on) WHERE post_id = %s''', [post_id])
                vote = [1, 1]
            elif post_vote.vote > 0:
                cls.objects.filter(post_id=post_id, user_id=user.user_id).update(vote=0, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(up_votes=F('up_votes') - 1)
                cursor.execute('''UPDATE app_post SET up_votes = up_votes - 1, votes = (up_votes - down_votes - 1), rank = compute_rank(up_votes - down_votes - 1, created_on) WHERE post_id = %s''', [post_id])
                vote = [0, -1]
            else:
                cls.objects.filter(post_id=post_id, user_id=user.user_id).update(vote=1, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(up_votes=F('up_votes') + 1, down_votes=F('down_votes') - 1)
                cursor.execute('''UPDATE app_post SET up_votes = up_votes + 1, down_votes = down_votes - 1, votes = (up_votes - down_votes + 2), rank = compute_rank(up_votes - down_votes + 2, created_on) WHERE post_id = %s''', [post_id])
                vote = [1, 2]
                
            transaction.commit_unless_managed()
            return vote            
        finally:
            cursor.close()        
        
     
    @classmethod
    def down_vote(cls, user, post_id):
        """
        Vote down if user not voted otherwise makes it zero
        """
        try:
            post_vote = cls.objects.get(post_id=post_id, user_id=user.user_id)
        except PostVote.DoesNotExist:
            post_vote = cls.objects.create(post_id=post_id, user_id=user.user_id, updated_by=str(user), created_by=str(user))
        
        cursor = connection.cursor()
        try:
            
            if post_vote.vote == 0:
                cls.objects.filter(post_id=post_id, user_id=user.user_id).update(vote= -1, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(down_votes=F('down_votes') + 1)     
                cursor.execute('''UPDATE app_post SET down_votes = down_votes + 1, votes = (up_votes - down_votes - 1), rank = compute_rank(up_votes - down_votes - 1, created_on) WHERE post_id = %s''', [post_id])
                vote = [-1, -1]
            elif post_vote.vote > 0:
                cls.objects.filter(post_id=post_id, user_id=user.user_id).update(vote= -1, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(up_votes=F('up_votes') - 1, down_votes=F('down_votes') + 1)                
                cursor.execute('''UPDATE app_post SET up_votes = up_votes - 1, down_votes = down_votes + 1, votes = (up_votes - down_votes - 2), rank = compute_rank(up_votes - down_votes - 2, created_on) WHERE post_id = %s''', [post_id])
                vote = [-1, -2]
            else:
                cls.objects.filter(post_id=post_id, user_id=user.user_id).update(vote=0, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(down_votes=F('down_votes') - 1)   
                cursor.execute('''UPDATE app_post SET down_votes = down_votes - 1, votes = (up_votes - down_votes + 1), rank = compute_rank(up_votes - down_votes + 1, created_on) WHERE post_id = %s''', [post_id])
                vote = [0, 1]
            
            transaction.commit_unless_managed()
            return vote
        finally:
            cursor.close()
                        
            
class CommentVote(models.Model):
    """
    Keep track of user vote on comment
    """
    vote_id = db_models.BigAutoField(primary_key=True)
    comment = models.ForeignKey(Comment)
    user = models.ForeignKey(User)
    vote = models.IntegerField(default=0)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=75)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    class Meta:
        unique_together = ('comment', 'user',)
    
    @classmethod
    def up_vote(cls, user, comment_id):
        """
        Vote up if user not voted otherwise makes it zero
        """
        try:
            comment_vote = cls.objects.get(comment_id=comment_id, user_id=user.user_id)
        except CommentVote.DoesNotExist:
            comment_vote = cls.objects.create(comment_id=comment_id, user_id=user.user_id, updated_by=str(user), created_by=str(user))
        
        cursor = connection.cursor()
        try:
                  
            if comment_vote.vote == 0:
                cls.objects.filter(comment_id=comment_id, user_id=user.user_id).update(vote=1, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(up_votes=F('up_votes') + 1)
                cursor.execute('''UPDATE app_comment SET up_votes = up_votes + 1, votes = (up_votes - down_votes + 1), rank = compute_rank(up_votes + 1, down_votes) WHERE comment_id = %s''', [comment_id])
                vote = [1, 1]
            elif comment_vote.vote > 0:
                cls.objects.filter(comment_id=comment_id, user_id=user.user_id).update(vote=0, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(up_votes=F('up_votes') - 1)
                cursor.execute('''UPDATE app_comment SET up_votes = up_votes - 1, votes = (up_votes - down_votes - 1), rank = compute_rank(up_votes - 1, down_votes) WHERE comment_id = %s''', [comment_id])
                vote = [0, -1]
            else:
                cls.objects.filter(comment_id=comment_id, user_id=user.user_id).update(vote=1, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(up_votes=F('up_votes') + 1, down_votes=F('down_votes') - 1)                
                cursor.execute('''UPDATE app_comment SET up_votes = up_votes + 1, down_votes = down_votes - 1, votes = (up_votes - down_votes + 2), rank = compute_rank(up_votes + 1, down_votes - 1) WHERE comment_id = %s''', [comment_id])
                vote = [1, 2]
                
            transaction.commit_unless_managed()
            return vote            
        finally:
            cursor.close()        
        
     
    @classmethod
    def down_vote(cls, user, comment_id):
        """
        Vote down if user not voted otherwise makes it zero
        """
        try:
            comment_vote = cls.objects.get(comment_id=comment_id, user_id=user.user_id)
        except CommentVote.DoesNotExist:
            comment_vote = cls.objects.create(comment_id=comment_id, user_id=user.user_id, updated_by=str(user), created_by=str(user))
        
        cursor = connection.cursor()
        try:
            
            if comment_vote.vote == 0:
                cls.objects.filter(comment_id=comment_id, user_id=user.user_id).update(vote= -1, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(down_votes=F('down_votes') + 1)
                cursor.execute('''UPDATE app_comment SET down_votes = down_votes + 1, votes = (up_votes - down_votes - 1), rank = compute_rank(up_votes, down_votes + 1) WHERE comment_id = %s''', [comment_id])                
                vote = [-1, -1]
            elif comment_vote.vote > 0:
                cls.objects.filter(comment_id=comment_id, user_id=user.user_id).update(vote= -1, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(up_votes=F('up_votes') - 1, down_votes=F('down_votes') + 1)
                cursor.execute('''UPDATE app_comment SET up_votes = up_votes - 1, down_votes = down_votes + 1, votes = (up_votes - down_votes - 2), rank = compute_rank(up_votes - 1, down_votes + 1) WHERE comment_id = %s''', [comment_id])
                vote = [-1, -2]
            else:
                cls.objects.filter(comment_id=comment_id, user_id=user.user_id).update(vote=0, updated_by=str(user))
                User.objects.filter(user_id=user.user_id).update(down_votes=F('down_votes') - 1)
                cursor.execute('''UPDATE app_comment SET down_votes = down_votes - 1, votes = (up_votes - down_votes + 1), rank = compute_rank(up_votes, down_votes - 1) WHERE comment_id = %s''', [comment_id])
                vote = [0, 1]
            
            transaction.commit_unless_managed()
            return vote
        finally:
            cursor.close()



class Message(models.Model):
    """
    User persistent messages
    """
    MESSAGE_TYPES = (('CO', 'Comment'),
                     ('RE', 'Reply'),
                     ('TE', 'Text'),)
    
    message_id = db_models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    sender = models.ForeignKey(User, related_name='sent_message')
    post = models.ForeignKey(Post, null=True)
    comment = models.ForeignKey(Comment, null=True)
    comment_msg = models.ForeignKey(Comment, null=True, related_name='comment_msg')
    message_type = models.CharField(max_length=2, choices=MESSAGE_TYPES)
    message_text = models.CharField(max_length=1024, null=True, blank=True)
    read_on = models.DateTimeField(null=True, blank=True)
    viewed_on = models.DateTimeField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    class Meta:
        index_together = [['message_id', 'user', 'read_on', 'viewed_on']]
    
    def __unicode__(self):
        return '[user_id: %s, type: %s]' % (self.user_id, self.message_type)
    
    
    @classmethod
    def add_comment_msg(cls, comment, user):
        """
        Adds a new user's message of comment or reply
        """
        post = Post.objects.get(post_id=comment.post_id)
        if post.user_id and post.user_id != comment.user_id:
            return cls.objects.create(user_id=post.user_id,
                                      post=post,
                                      comment_msg=comment,
                                      sender=user,
                                      message_type='CO',
                                      created_by=str(user))
            
    
    @classmethod
    def add_reply_msg(cls, reply, user):
        """
        Adds a new user's message of comment or reply
        """
        comment = Comment.objects.get(comment_id=reply.reply_to_id) 
        if comment.user_id != reply.user_id:      
            return cls.objects.create(user_id=comment.user_id,
                                      post_id=comment.post_id,
                                      comment=comment,
                                      comment_msg=reply,
                                      sender=user,
                                      message_type='RE',
                                      created_by=str(user))
    
    @classmethod
    def get_messages(cls, user, max=20):
        """
        Returns user's latest messages
        """
        messages = [message for message in cls.objects.select_related('post', 'comment', 'user', 'sender', 'comment_msg').filter(user=user).order_by('-message_id')[:max]]
        for message in messages:
            message.comment_msg.post = message.post
            if message.comment_id != None:
                message.comment.post = message.post
        
        return messages
                
        
    @classmethod
    def mark_read(cls, msg_id, user, all_msg):
        """
        Mark messages as read in database
        """
        now = datetime.datetime.now()
        if all_msg:
            cls.objects.filter(message_id__lte=msg_id, user=user, read_on__isnull=True).update(read_on=now)
        else:
            cls.objects.filter(message_id=msg_id, user=user, read_on__isnull=True).update(read_on=now)
        
    @classmethod
    def mark_viewed(cls, msg_id, user):
        """
        Mark messages as viewed in database
        """
        now = datetime.datetime.now()
        cls.objects.filter(message_id__lte=msg_id, user=user, viewed_on__isnull=True).update(viewed_on=now)


class FbUser(models.Model):
    """
    Facebook user information
    """
    user = models.ForeignKey(User, primary_key=True)
    name = models.CharField(max_length=100)
    fb_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=50)
    email = models.EmailField()
    access_token = models.CharField(max_length=2048,blank=True,null=True) # Sizes can grow and shrink therefore 2K should be enough
    access_expiry = models.DateTimeField(blank=True,null=True)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=75)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    def __unicode__(self):
        return self.username
    
    @classmethod
    def connect_user(cls, user, fb_id, name, username, email, access_token, access_expiry):
        """
        Associate Facebook user with TangleOn user, not already exists and return True, user
        """
        try:
            fb_user = cls.objects.select_related('user').get(fb_id=fb_id)
            if fb_user.user_id != user.user_id:
                raise TangleOnError("Facebook account '%s' is already connected with a different TangleOn user" % username)
            fb_user.access_token = access_token
            fb_user.access_expiry = access_expiry
            fb_user.save()
            return False
        except cls.DoesNotExist:
            cls.objects.create(user=user,
                               fb_id=fb_id,
                               name=name,
                               username=username,
                               email=email,
                               access_token=access_token,
                               access_expiry=access_expiry)
            return True
    
    @classmethod
    def get_user_or_create(cls, fb_id, name, username, email, access_token, access_expiry):
        """
        Returns TangleOn user associated with Facebook user or creates a new TangleOn user
        """
        try:
            fb_user = cls.objects.select_related('user').get(fb_id=fb_id)
            fb_user.access_token = access_token
            fb_user.access_expiry = access_expiry
            fb_user.save()
            return False, fb_user.user
        except cls.DoesNotExist:
            # Checking for username in database
            username =  'fb_' + username if User.objects.filter(username__iexact=username).exists() else username
            
            # Setting random password, since user will use Facebook to login otherwise he can recover his password
            user = User.sign_up(username, email, Credential.random_digest())
            user.has_activated = True
            user.save()
            cls.objects.create(user=user,
                               fb_id=fb_id,
                               name=name,
                               username=username,
                               email=email,
                               access_token=access_token,
                               access_expiry=access_expiry)
            return True, user
    

class FlashMessage(models.Model):
    """
    Class to store flash messages for user
    """
    INFO = 'info'
    ERROR = 'error'
    WARNING = 'warning'
    SUCCESS = 'success'
    FLASH_TYPES = ((INFO, 'Information'),
                   (ERROR, 'Error'),
                   (WARNING, 'Warning'),
                   (SUCCESS, 'Success'),)
    
    flash_id = db_models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    flash_text = models.TextField()
    flash_type = models.CharField(max_length=10,choices=FLASH_TYPES)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=75)
    
    def __unicode__(self):
        return self.flash_text
    
    @classmethod
    def add_message(cls, flash_type, flash_text, user):
        """
        Adds a new message for user in database
        """
        return cls.objects.create(flash_type=flash_type, flash_text=flash_text, user=user, created_by=str(user))
    
    @classmethod
    def add_info(cls, flash_text, user):
        """
        Adds a new info message for user in database
        """
        return cls.add_message(cls.INFO, flash_text, user)
    
    @classmethod
    def add_error(cls, flash_text, user):
        """
        Adds a new error message for user in database
        """
        return cls.add_message(cls.ERROR, flash_text, user)
    
    @classmethod
    def add_warning(cls, flash_text, user):
        """
        Adds a new warning message for user in database
        """
        return cls.add_message(cls.WARNING, flash_text, user)
    
    @classmethod
    def add_success(cls, flash_text, user):
        """
        Adds a new success message for user in database
        """
        return cls.add_message(cls.SUCCESS, flash_text, user)
    
    @classmethod
    def peek_messages(cls, user):
        """
        Returns all flash messages for user but don't delete them in database
        """        
        return [flash for flash in cls.objects.filter(user=user).order_by('flash_id')]

    @classmethod
    def get_messages(cls, user):
        """
        Returns all flash messages for user and delete them database
        """
        messages = cls.peek_messages(user)        
        cls.objects.filter(user=user).delete()
        return messages

