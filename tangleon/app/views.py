"""
Contains views for TangleOn app
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""

import re
import urllib
import datetime
import logging
import urlparse

from django.http import HttpResponseRedirect, Http404, HttpResponse, HttpResponseForbidden, HttpResponseServerError, HttpResponseBadRequest, HttpResponsePermanentRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.mail import EmailMessage
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils import simplejson
from django.db import transaction
from django.template.loader import get_template
from django.template import Context
from django.conf import settings

from tangleon import TangleOnError
from tangleon.app import login_user, logout_user, scraper
from tangleon.app.forms import SignUp, ChangePassword, PasswordReset, SubmitLinkPost, SubmitTextPost
from tangleon.app.models import User, Credential, Follow, Channel, Post, Comment, Tag, Subscription, Pin, PostVote, CommentVote, Message, FbUser, FlashMessage
from tangleon.app.decorators import login_required, anonymous_required


MARK_DOWN_TEXT = """*italics*

**bold**

[TangleOn](//tangleon.com)

* item 1 
* item 2 
* item 3

> quoted text

Lines started with four 
spaces for a code block: 

    if i * 2 > 0: 
      print "hello...!" 
""" 

logger = logging.getLogger('django.request')


def index(request, by_new=False, page_index=0):
    """
    Display hot or new posts of all channels and users
    """
    now = datetime.datetime.now()
    page_index = int(page_index)    
    source = {'title': 'All',
              'absolute_url': reverse('app_index'),
              'absolute_url_by_new': reverse('app_index_new'),
              'active': 'new' if by_new else 'top'}
    posts = Post.get_posts(int(page_index), settings.PAGE_SIZE, by_new, request.app_user)
    top_tags = Tag.top_tags()
    top_channels = Channel.top_channels()
    prev_url, next_url = paginated_url(request.resolver_match.url_name, posts, [page_index])
    
    response = render_response(request, 'app/index.html', locals())
        
    return response


def search(request, by_new=False, page_index=0):
    """
    Search for query text in title and tags fields of post
    """
    q = request.REQUEST.get('q', None)
    if q:        
        channels_q = Channel.objects.filter(title__iexact=q)[:1]
        if channels_q:
            return HttpResponseRedirect(reverse('app_channel', args=[channels_q[0].channel_id]))
        
        tags_q = Tag.objects.filter(name__iexact=q)[:1]
        if tags_q:            
            return HttpResponseRedirect(reverse('app_tag', args=[tags_q[0].name]))
        
        users_q = User.objects.filter(username__iexact=q)[:1]
        if users_q:            
            return HttpResponseRedirect(reverse('app_user', args=[users_q[0].username]))
        
        params = { 'q': q.encode('utf-8')}
        query = '?' + urllib.urlencode(params)
        source = {'title': q,
                  'absolute_url': reverse('app_search') + query,
                  'absolute_url_by_new': reverse('app_search_new') + query,
                  'active': 'new' if by_new else 'top'}
        posts = Post.tag_posts(q, int(page_index), settings.PAGE_SIZE, by_new, request.app_user)
                
        top_tags = Tag.top_tags()
        top_channels = Channel.top_channels()                
        prev_url, next_url = paginated_url(request.resolver_match.url_name, posts, [page_index], params)
                
        return render_response(request, 'app/search.html', locals())
    
    return HttpResponseRedirect(reverse('app_index'))


def tag_posts(request, tag_name, by_new=False, page_index=0):
    """
    Display posts were tag found in title or tags field
    """    
    source = {'title': tag_name,
              'absolute_url': reverse('app_tag', args=[tag_name]),
              'absolute_url_by_new': reverse('app_tag_new', args=[tag_name]),
              'active': 'new' if by_new else 'top'}
    posts = Post.tag_posts(tag_name, int(page_index), settings.PAGE_SIZE, by_new, request.app_user)
    try:
        tag = Tag.objects.get(name__iexact=tag_name)
        pin = None if request.app_user.is_anonymous() else Pin.objects.get(user=request.app_user, tag=tag) 
    except Tag.DoesNotExist:
        tag = {'name': tag_name, 'pin_count': 0 }
        pin = None
    except Pin.DoesNotExist:
        pin = None
    
    top_tags = Tag.top_tags()
    prev_url, next_url = paginated_url(request.resolver_match.url_name, posts, [tag_name, page_index])
                
    return render_response(request, 'app/tag.html', locals())


def channel_posts(request, channel_id, by_new=False, page_index=0):
    """
    Display posts from particular source like TechCrunch or Engadget
    """
    channel = get_object_or_404(Channel, channel_id=channel_id)    
    channel.sync(request.app_user)
    source = {'title': channel.title,
              'absolute_url': channel.get_absolute_url(),
              'absolute_url_by_new': reverse('app_channel_new', args=[channel.channel_id]),
              'active': 'new' if by_new else 'top'}
    posts = channel.get_posts(int(page_index), settings.PAGE_SIZE, by_new, request.app_user)
    try:
        subscription = Subscription.objects.get(channel=channel, user=request.app_user) if request.app_user.is_authenticated() else None
    except Subscription.DoesNotExist:
        subscription = None;
        
    prev_url, next_url = paginated_url(request.resolver_match.url_name, posts, [channel_id, page_index])
    top_channels = Channel.top_channels()
    
    return render_response(request, 'app/channel.html', locals())


def user_posts(request, username, by_new=False, page_index=0):
    """
    Display posts submit by the logged in user
    """
    user = get_object_or_404(User, username=username)    
    source = {'title': user.username,
              'absolute_url': user.get_absolute_url(),
              'absolute_url_by_new': reverse('app_user_new', args=[user.username]),
              'comments_url': reverse('app_user_comments', args=[user.username]),
              'votes_url': reverse('app_user_votes', args=[user.username]),
              'messages_url': reverse('app_user_messages', args=[user.username]),
              'active': 'new' if by_new else 'top'}
    
    if request.app_user.is_authenticated():
        follow = Follow.objects.filter(follower=request.app_user, following=user).all()
        if follow: follow = follow[0]
        
    posts = user.get_posts(int(page_index), settings.PAGE_SIZE, by_new, request.app_user)
    prev_url, next_url = paginated_url(request.resolver_match.url_name, posts, [username, page_index])
    
    return render_response(request, 'app/user.html', locals()) 


def user_comments(request, username, page_index=0):
    """
    Display posts on which user commented
    """
    user = get_object_or_404(User, username=username)
    source = {'title': user.username,
              'absolute_url': user.get_absolute_url(),
              'absolute_url_by_new': reverse('app_user_new', args=[user.username]),
              'comments_url': reverse('app_user_comments', args=[user.username]),
              'votes_url': reverse('app_user_votes', args=[user.username]),
              'messages_url': reverse('app_user_messages', args=[user.username]),
              'active': 'comments'}
    
    if request.app_user.is_authenticated():
        follow = Follow.objects.filter(follower=request.app_user, following=user).all()
        if follow: follow = follow[0]

    posts = user.get_by_comments(int(page_index), settings.PAGE_SIZE, request.app_user)
    prev_url, next_url = paginated_url('app_user_comments', posts, [username, page_index])
    
    return render_response(request, 'app/user.html', locals())


def user_messages(request, username, page_index=0):
    """
    Display user's messages
    """
    user = get_object_or_404(User, username=username)
    source = {'title': user.username,
              'absolute_url': user.get_absolute_url(),
              'absolute_url_by_new': reverse('app_user_new', args=[user.username]),
              'comments_url': reverse('app_user_comments', args=[user.username]),
              'votes_url': reverse('app_user_votes', args=[user.username]),
              'messages_url': reverse('app_user_messages', args=[user.username]),
              'active': 'messages'}
    
    if request.app_user.is_authenticated():
        follow = Follow.objects.filter(follower=request.app_user, following=user).all()
        if follow: follow = follow[0]

    posts = user.get_by_messages(int(page_index), settings.PAGE_SIZE, request.app_user)
    prev_url, next_url = paginated_url('app_user_messages', posts, [username, page_index])
    
    return render_response(request, 'app/user.html', locals()) 


def user_votes(request, username, page_index=0):
    """
    Display posts on which user voted
    """
    user = get_object_or_404(User, username=username)
    get_absolute_url = user.get_absolute_url()
    source = {'title': user.username,
              'absolute_url': user.get_absolute_url(),
              'absolute_url_by_new': reverse('app_user_new', args=[user.username]),
              'comments_url': reverse('app_user_comments', args=[user.username]),
              'votes_url': reverse('app_user_votes', args=[user.username]),
              'messages_url': reverse('app_user_messages', args=[user.username]),
              'active': 'votes'}
    
    if request.app_user.is_authenticated():
        follow = Follow.objects.filter(follower=request.app_user, following=user).all()
        if follow: follow = follow[0]

    posts = user.get_by_votes(int(page_index), settings.PAGE_SIZE, request.app_user)
    prev_url, next_url = paginated_url('app_user_votes', posts, [username, page_index])
    
    return render_response(request, 'app/user.html', locals())    


def read_post(request, post_id, slug, comment_id=None):
    """
    Display post and its comments
    """
    try:
        try:
            max_comments = 200 if int(request.GET.get('limit', 200)) > 200 else request.GET.get('limit', 200)
        except:
            max_comments = 200
        
        if request.app_user.is_authenticated() and 'message_id' in request.GET:
            Message.mark_read(request.GET['message_id'], request.app_user, False)
            
        post_id = long(post_id)        
        comment_id = long(comment_id) if comment_id else None
        post = Post.read_post(post_id, slug, request.app_user, comment_id, max_comments)        
    except Post.DoesNotExist:
        raise Http404()    
    
    markdown_help_text = MARK_DOWN_TEXT
    
    return render_response(request, 'app/post.html', locals())

def rate_post(request, post_id, slug, comment_id=None):
    """
    Display post web page and rating bar
    """
    try:    
        post_id = long(post_id)        
        post = Post.read_post(post_id, slug, request.app_user, max_comments=0)
        if post.is_text_post():
            return HttpResponsePermanentRedirect(post.get_absolute_url())
                
    except Post.DoesNotExist:
        raise Http404()
    
    return render_response(request, 'app/rate_post.html', locals())

def pic_post(request, post_id):
    """
    Returns actual url of post picture
    """
    post = get_object_or_404(Post,post_id=int(post_id))
    if post.img_url is None:
        raise Http404()
    
    return HttpResponsePermanentRedirect(post.img_url)

def short_url(request, post_id=None, comment_id=None):
    """
    Redirect short url to actual post or specific comment thread
    """
    if post_id:
        post = get_object_or_404(Post, post_id=post_id)
        return HttpResponsePermanentRedirect(reverse('app_post', args=[post_id, post.slug]))
    
    if comment_id:
        comment = get_object_or_404(Comment, comment_id=comment_id)
        return HttpResponsePermanentRedirect(reverse('app_comment', args=[comment.post_id, comment.post.slug, comment_id]))
    
    raise Http404()
           

@login_required
def get_title(request):
    """
    Fetch title of the url webpage.
    """       
    url = request.POST.get('url', None)
    if request.method == 'POST' and url:
        try:
            return HttpResponse(scraper.get_page_title(url))            
        except TangleOnError as e:
            return HttpResponseServerError(e.message)
        except:
            HttpResponseServerError('Unable to fetch title')
            
    return HttpResponseBadRequest('Url is empty.')

@login_required
@transaction.commit_on_success
def submit_link_post(request):
    """
    Save a new link post from user to database
    """ 
    error = None
    if request.method == 'POST':
        form = SubmitLinkPost(request.POST)
        if form.is_valid():
            try:
                data = form.cleaned_data
                post = Post.submit_post(request.app_user, data['title'], data['tags'], data['url'])
                return HttpResponseRedirect(reverse('app_post', args=[post.post_id, post.slug]))
            except TangleOnError as e:
                error = e.message
    else:
        form = SubmitLinkPost(initial={'url': request.GET.get('url', None), 'title': request.GET.get('title', None), 'tags': request.GET.get('tags', None)})
    
    top_tags = Tag.top_tags()
    return render_response(request, 'app/submit_link_post.html', {'form': form, 'error': error, 'top_tags': top_tags})


@login_required
@transaction.commit_on_success
def submit_text_post(request):
    """
    Save a new text post from user to database
    """    
    error = None
    if request.method == 'POST':
        form = SubmitTextPost(request.POST)
        if form.is_valid():
            try:
                data = form.cleaned_data
                post = Post.submit_post(request.app_user, data['title'], data['tags'], description=data['description'])
                return HttpResponseRedirect(reverse('app_post', args=[post.post_id, post.slug]))
            except TangleOnError as e:
                error = e.message
    else:
        form = SubmitTextPost(initial={'tags': request.GET.get('tags', None)})
    
    top_tags = Tag.top_tags()
    return render_response(request, 'app/submit_text_post.html', {'form': form, 'error': error, 'markdown_help_text': MARK_DOWN_TEXT, 'top_tags': top_tags })


@login_required
@transaction.commit_on_success
def user_subscribe(request):
    """
    Subscribe user to channel or tag
    """
    channel_id = request.GET.get('channel_id', None)
    tag_name = request.GET.get('tag', None)
    username = request.GET.get('username', None)
    
    if channel_id:
        channel_id = int(channel_id)
        if request.method == 'POST':
            Subscription.subscribe(channel_id, request.app_user)
        return HttpResponseRedirect(reverse('app_channel', args=[channel_id]))
    elif tag_name:
        if request.method == 'POST':            
            Pin.pin_tag(tag_name, request.app_user)
        return HttpResponseRedirect(reverse('app_tag', args=[tag_name]))
    elif username:
        if request.method == 'POST':
            Follow.follow(username, request.app_user)
        return HttpResponseRedirect(reverse('app_user', args=[username])) 
    
    return HttpResponseRedirect(reverse('app_index'))


@login_required
@transaction.commit_on_success
def user_unsubscribe(request):
    """
    Subscribe user to channel or tag
    """
    channel_id = request.GET.get('channel_id', None)
    tag_name = request.GET.get('tag', None)
    username = request.GET.get('username', None)
    
    if channel_id:
        channel_id = int(channel_id)
        if request.method == 'POST':
            Subscription.unsubscribe(channel_id, request.app_user)
        return HttpResponseRedirect(reverse('app_channel', args=[channel_id]))
    elif tag_name:            
        if request.method == 'POST':
            Pin.unpin_tag(tag_name, request.app_user)
        return HttpResponseRedirect(reverse('app_tag', args=[tag_name]))  
    elif username:
        if request.method == 'POST':
            Follow.unfollow(username, request.app_user)
        return HttpResponseRedirect(reverse('app_user', args=[username])) 
    
    return HttpResponseRedirect(reverse('app_index'))


@login_required
@transaction.commit_on_success
def user_friends(request, username):
    """
    Returns list of friends for user on Facebook that exists in TangleOn    
    """    
    if request.app_user.username != username or not hasattr(request.app_user, 'fbuser'):
        return HttpResponseRedirect(reverse('app_user', args=[request.app_user.username]))
    
    fbuser = request.app_user.fbuser
    return_next = request.GET.get('next', reverse('app_index'))
    if request.method == 'GET':
        if fbuser.access_expiry < datetime.datetime.now():
            params = urllib.urlencode({'client_id': settings.FB_APP_ID,
                                   'response_type': 'code',
                                   'redirect_uri': request.build_absolute_uri(request.path),
                                   'state': return_next
                                   })        
            return HttpResponseRedirect(settings.FB_AUTH_URL + '?' + params)
            
        
        params = urllib.urlencode({'access_token': fbuser.access_token,
                                   'fields': 'id,username,name',
                                   'limit': '1000'})        
        try:
            friends_json = simplejson.loads(scraper.get_content(settings.FB_GRAPH_FRIENDS + '?' + params))['data']
            
            if not len(friends_json):
                return HttpResponseRedirect(request.GET.get('next', reverse('app_index')))
                            
            friendids = list(int(friend['id']) for friend in friends_json)
            friends = list(FbUser.objects.select_related('user').filter(fb_id__in=friendids))
            if len(friends):
                for follow in Follow.objects.filter(follower_id=request.app_user.user_id,following_id__in=list(friend.user_id for friend in friends)):
                    for friend in friends:
                        if friend.user_id == follow.following_id:
                            friend.follow = follow
                            break
                                    
                return render_response(request, 'app/friends.html', locals())
            
            return HttpResponseRedirect(return_next)
        except Exception as e:
            logger.exception(e)
            return render_response(request, 'app/friends.html', {'error': 'We are unable to load your friends list from your Facebook account, please try again later.'})
            
    return HttpResponseRedirect(reverse('app_index'))
    
        

@login_required
@transaction.commit_on_success
def comment_save(request, post_id, slug):
    """
    Save user comment for the post in database
    """
    post_url = reverse('app_post', kwargs={ 'post_id': post_id, 'slug': slug})
    if request.method == 'GET':
        return HttpResponseRedirect(post_url)
    
    comment_text = request.POST.get('comment_text', None)        
    if comment_text:
        comment = Comment.save_comment(request.app_user, post_id, slug, comment_text[:settings.MAX_COMMENT_LEGNTH])        
        if request.is_ajax():
            return render_response(request, 'app/webparts/comment.html', { 'post': Post.objects.get(post_id=post_id), 'comment': comment })        
        post_url += '#comment-id-' + str(comment.comment_id)
                
    return HttpResponseRedirect(post_url)


@login_required
@transaction.commit_on_success
def reply_save(request, post_id, slug):
    """
    Save user reply for the comment on the particular post to database
    """
    post_url = reverse('app_post', kwargs={ 'post_id': post_id, 'slug': slug})
    if request.method == 'GET':
        return HttpResponseRedirect(post_url)
        
    comment_id = request.POST.get('comment_id', None)
    comment_text = request.POST.get('comment_text', None)
    
    if comment_id and comment_text:         
        comment = Comment.save_reply(request.app_user, post_id, slug, comment_id, comment_text[:settings.MAX_COMMENT_LEGNTH])
        if request.is_ajax():
            return render_response(request, 'app/webparts/comment.html', { 'post': Post.objects.get(post_id=post_id), 'comment': comment })
        post_url += '#comment-id-' + str(comment.comment_id)                
    
    return HttpResponseRedirect(post_url)

@transaction.commit_on_success
def post_vote(request):
    """
    Make user's like vote for the post
    """
        
    if request.method == 'POST' and 'post_id' in request.POST and 'action' in request.POST:        
        post_id = int(request.POST['post_id'])
        action = request.POST['action']        
        if request.app_user.is_anonymous():
            return HttpResponseForbidden(reverse('app_login') + '?' + urllib.urlencode({'next': reverse('app_post', args=[post_id])}))
                
        if action == 'up': 
            vote_index, net_effect = PostVote.up_vote(request.app_user, post_id)
        else:
            vote_index, net_effect = PostVote.down_vote(request.app_user, post_id)
        
        if request.is_ajax():
            response = {'post_id': post_id, 'vote_index': vote_index, 'net_effect':net_effect }
            return HttpResponse(simplejson.dumps(response), mimetype='application/json')
            
        return HttpResponseRedirect(reverse('app_post', args=[post_id]))
    
    return HttpResponseRedirect(reverse('app_index'))

@transaction.commit_on_success
def comment_vote(request):
    """
    Make user's like or dislike vote for the comment
    """
    if request.method == 'POST' and 'comment_id' in request.POST and 'post_id' in request.POST and 'action' in request.POST:
        post_id = int(request.POST['post_id'])
        comment_id = int(request.POST['comment_id'])
        action = request.POST['action']
        if request.app_user.is_anonymous():
            return HttpResponseForbidden(reverse('app_login') + '?' + urllib.urlencode({'next': reverse('app_post', args=[post_id])}))
                
        if action == 'up':
            vote_index, net_effect = CommentVote.up_vote(request.app_user, comment_id)
        else:
            vote_index, net_effect = CommentVote.down_vote(request.app_user, comment_id)
        
        if request.is_ajax():
            response = {'comment_id': comment_id, 'vote_index': vote_index, 'net_effect':net_effect }
            return HttpResponse(simplejson.dumps(response), mimetype='application/json')
            
        return HttpResponseRedirect(reverse('app_comment', args=[comment_id]))
    
    return HttpResponseRedirect(reverse('app_index'))


@login_required
def mark_read(request):
    """
    Mark all messages as read
    """
    message_id = request.REQUEST.get('message_id', None)
    if message_id:
        Message.mark_read(int(message_id), request.app_user, 'all' in request.REQUEST)
        
        if request.is_ajax():
            return HttpResponse('OK')
        
    return HttpResponseRedirect(reverse('app_index'))
    

@login_required
def mark_viewed(request):
    """
    Mark all messages as read
    """
    message_id = request.POST.get('message_id', None)
    if request.method == 'POST' and message_id:
        Message.mark_viewed(int(message_id), request.app_user)
        
        if request.is_ajax():
            return HttpResponse('OK')
    
    return HttpResponseRedirect(reverse('app_index'))
    

TAG_REGEX = re.compile(r'^[@]?[\w\.]{3,20}$')
@login_required
def tag_search(request):
    """
    Returns matched tags define in database
    """
    if request.method == 'GET' and 'q' in request.GET:
        q = request.GET['q'].strip()
        q_lower = q.lower()
        found = False
        
        tags = []
        db_tags = Tag.objects.filter(name__istartswith=q).order_by('name')[:20]
        for tag in db_tags:
            if not tag.is_muted:
                tags.append({'id':tag.name.lower(), 'name':tag.name})
            if len(q_lower) == len(tag.name):
                found = True
                
        if TAG_REGEX.match(q) and not found:
            tags.append({'id': q_lower, 'name': q})
        
        response = simplejson.dumps(tags)
        print response
        return HttpResponse(response)
    
    return HttpResponseBadRequest()


@anonymous_required
def login(request):
    """
    User login for view for tangleon.com
    """
    if request.method == 'POST':
        login_error = ''
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        if username and password:
            # Avoding long password hash attacks
            user = Credential.authenticate(username, password) if len(password) < 50 else None
            if not user:
                login_error = '''Username and password didn't matched, if you forgot your password? <a href="/forgot_password/">Request new one</a>'''            
            elif not user.is_active:
                login_error = '''Your account has been disabled. We apologize for any inconvenience! If this is a mistake please contact our <a href="mailto:hi@tangleon.com">support</a>.''' 
            elif user.has_activated:
                FlashMessage.add_info('Welcome back, ' + user.username, user)
                login_user(request, user)                
                url = request.GET.get('next', '/')
                return HttpResponseRedirect(url)
            else:
                return render_response(request, 'app/login.html', { 'username': username, 'send_activation_code': True, 'email': user.email })
        
        return render_response(request, 'app/login.html', { 'username': username, 'login_error': login_error })
    
    return render_response(request, 'app/login.html')


def logout(request):
    """
    Logout the user and flush his session data
    """
    logout_user(request)    
    return HttpResponseRedirect('/')


@login_required
def change_password(request):
    """
    Updates user's password in database
    """
    error = None
    if request.method == 'POST':
        form = ChangePassword(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:                
                Credential.change_password(request.app_user, data['current_password'], data['password'])
                successfully_changed = True
            except TangleOnError as e:
                error = e.message
    else:
        form = ChangePassword()
    
    return render_response(request, 'app/change_password.html', locals())


@anonymous_required
@transaction.commit_on_success
def signup(request):
    """
    Creates a new user in database and send activation to his email address
    """    
    error = None
    successful_signup = None
    if request.method == 'POST':
        form = SignUp(request.POST)
        if form.is_valid():
            try:
                data = form.cleaned_data
                user = User.sign_up(data['username'], data['email'], data['password'])
                domain = get_current_site(request).domain
                msg_text = get_template('app/email/activation.html').render(Context({ 'domain': domain, 'user': user }))
                msg = EmailMessage('tangleon.com account activation', msg_text, 'TangleOn <noreply@tangleon.com>', [user.email])
                msg.content_subtype = "html"
                msg.send()
                                
                msg_text = get_template('app/email/welcome.html').render(Context({ 'domain': domain, 'user': user }))
                msg = EmailMessage('tangleon.com Welcome! Lets get started!!', msg_text, 'TangleOn <noreply@tangleon.com>', [user.email])
                msg.content_subtype = "html"
                msg.send()
                successful_signup = True                
            except TangleOnError as e:            
                error = e.message
    else:
        form = SignUp()
    
    if request.is_ajax():
        return render_response(request, 'app/webparts/signup.html', {'signup_form': form, 'error': error, 'successful_signup': successful_signup })
    
    return render_response(request, 'app/signup.html', {'signup_form': form, 'error': error, 'successful_signup': successful_signup })


@anonymous_required
def forgot_password(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')

    reset_email_send = None    
    reset_email_error = None
    if request.method == 'POST': 
        email = request.POST.get('email', None)
        if email:
            try:
                user, credential = Credential.generate_reset_code(email)
                msg_text = get_template('app/email/password_reset.html').render(Context({ 'domain': get_current_site(request).domain, 'user': user, 'reset_code' :credential.reset_code }))
                msg = EmailMessage('tangleon.com password reset', msg_text, 'TangleOn <noreply@tangleon.com>', [user.email])
                msg.content_subtype = "html"
                msg.send()
                reset_email_send = True
            except TangleOnError as e:
                reset_email_error = e.message            
        else:            
            reset_email_error = 'Please enter your email address.'
                
    return render_response(request, 'app/forgot_password.html', {'reset_email_send': reset_email_send, 'reset_email_error':reset_email_error})


@anonymous_required
def password_reset(request):
    """
    Resets user's password
    """
    error = None
    successful_reset = False    
    if request.method == 'POST':
        email = request.GET.get('email', None)
        reset_code = request.GET.get('reset_code', None)
        form = PasswordReset(request.POST)
        if form.is_valid() and email and reset_code:
            password = form.cleaned_data['password']
            try:
                Credential.password_reset(email, reset_code, password)
                successful_reset = True
            except TangleOnError as e:
                error = e.message                        
    else:
        form = PasswordReset()
        
    return render_response(request, 'app/password_reset.html', { 'form': form, 'error': error, 'successful_reset': successful_reset})
        


@anonymous_required
def activation(request):
    """
    Activates the new user
    """
    activation_error = None
    if request.method == 'GET':
        email = request.GET.get('email', None)
        activation_code = request.GET.get('activation_code', None)
        if email and activation_code:
            try:
                user = User.activate(email, activation_code)
                login_user(request, user)
                return HttpResponseRedirect(reverse('app_index'))
            except TangleOnError as error:
                activation_error = error.message
        else:
            activation_error = 'TangleOn account activation url is not correct; please try to copy and paste complete url from email.'
    else:
        activation_error = 'Invalid activation request.'       
    
    return render_response(request, 'app/activation.html', {'activation_error': activation_error})

@anonymous_required
def send_activation_code(request):
    """
    Resends tangleon.com account activation code to the user
    """
    send_activation_error = None
    email = request.GET.get('email', None)
    if email:
        try:
            user = User.generate_activation_code(email)
            msg_text = get_template('app/email/activation.html').render(Context({ 'domain': get_current_site(request).domain, 'user': user }))
            msg = EmailMessage('tangleon.com account activation', msg_text, 'TangleOn <noreply@tangleon.com>', [user.email])
            msg.content_subtype = "html"
            msg.send()
                
        except TangleOnError as e:
            send_activation_error = e.message
    else:
        send_activation_error = 'Invalid link for resend activation code'
    
    return render_response(request, 'app/send_activation.html', { 'send_activation_error': send_activation_error })
    

def sitemap_xml(request):    
    posts = Post.users_posts(0, 1000, True)
            
    return render_to_response('app/sitemap.xml', locals(), mimetype='application/xml')


@transaction.commit_on_success
def facebook_login(request):
    """
    Login user through Facebook
    """
    if request.method == 'POST':
        params = urllib.urlencode({'client_id': settings.FB_APP_ID,
                                   'response_type': 'code',
                                   'redirect_uri': request.build_absolute_uri(request.path),
                                   'state': request.POST.get('next', reverse('app_index')), # redirect uri for user
                                   'scope': 'email'
                                   })
        
        return HttpResponseRedirect(settings.FB_AUTH_URL + '?' + params)
    
    code = request.GET.get('code', None)
    if not code:
        error = request.GET.get('error', None)
        error_reason = request.GET.get('error_reason', None)
        if error == 'access_denied' and error_reason == 'user_denied':
            return render_response(request, 'app/facebook_login.html', {'error': 'You must allow TangleOn to access your basic information from Facebook.'})
            
        logger.error('Error occurred while signing user through Facebook.\n' + str(request))    
        return render_response(request, 'app/facebook_login.html', {'error': 'We encounter some error while logging you in through Facebook.'})
            
    return_url = request.GET['state']
    code = request.GET['code']
    params = urllib.urlencode({'client_id': settings.FB_APP_ID, 
                               'client_secret': settings.FB_APP_SECRET,
                               'redirect_uri': request.build_absolute_uri(request.path),
                               'code': code })
    
    try:        
        access_content = scraper.get_content(settings.FB_ACCESS_TOKEN + '?' + params)    
        access_content = dict(urlparse.parse_qsl(access_content))
        access_token = access_content['access_token']
        access_expiry = datetime.datetime.now() + datetime.timedelta(seconds=int(access_content['expires']))
        request.session['facebook_access_token'] = access_token      
        params = urllib.urlencode({'access_token': access_token,
                                   'fields': 'id,username,email,name'})
        
        fb_user = scraper.get_content(settings.FB_GRAPH_ME + '?' + params)
        fb_user = simplejson.loads(fb_user)
        try:
            if request.app_user.is_authenticated():
                user = request.app_user
                created = FbUser.connect_user(user, fb_user['id'], fb_user['name'], fb_user['username'], fb_user.get('email', user.email), access_token, access_expiry)
                if created:
                    FlashMessage.add_success('Your Facebook account is successfully connected.', user)
            else:
                if not 'email' in fb_user:
                    raise TangleOnError('You need to allow TangleOn for access of your email address on Facebook, please read our privacy <a href="%s">policy</a> for any concern.' % reverse('app_policy'))
                created, user = FbUser.get_user_or_create(fb_user['id'], fb_user['name'], fb_user['username'], fb_user['email'], access_token, access_expiry)
                if not user.is_active:
                    raise TangleOnError('Your account has been disabled. We apologize for any inconvenience! If this is a mistake please contact our <a href="mailto:hi@tangleon.com">support</a>.')
                login_user(request, user)
                if created:
                    FlashMessage.add_success('You have successfully signed up with Facebook account.', user)
                else:
                    FlashMessage.add_info('Welcome back, ' + user.username, user)

            if created:        
                return HttpResponseRedirect(reverse('app_user_friends', args=[user.username]) + '?' + urllib.urlencode({ 'next': return_url}))        
            
            return HttpResponseRedirect(return_url)            
        except TangleOnError as e:
            return render_response(request, 'app/facebook_login.html', {'error': e.message })
    except Exception as e:
        logger.exception(e)
        return render_response(request, 'app/facebook_login.html', {'error': 'We encounter some error while logging you in through Facebook.' })
    
    return HttpResponseRedirect(reverse('app_index'))
    

def mediaplay(request, post_id):
    """
    Returns partial media player html
    """
    post = get_object_or_404(Post, post_id=int(post_id))    
    return render_response(request, 'app/webparts/mediaplay.html', locals())


def content_page(request, title, content_page):
    """
    Display markdown content page
    """    
    content = get_template(content_page).render(Context({}))
    return render_response(request, 'app/content_page.html', locals()) 


def render_response(request, *args, **kwargs):
    """
    Render template using RequestContext so that context processors should be available in template
    """
    kwargs['context_instance'] = RequestContext(request)
    return render_to_response(*args, **kwargs)

        
def paginated_url(url_name, result_set, args, qs=None):
    """
    Returns previous and next page urls
    """
    prev_url = None
    next_url = None
    qs = '?' + urllib.urlencode(qs) if qs else ''
    page_index = int(args[-1])
    
    if page_index == 1:
        prev_url = reverse(url_name, args=args[:-1]) + qs
    elif page_index > 1 :
        args[-1] = page_index - 1
        prev_url = reverse(url_name, args=args) + qs
    
    if len(result_set) == settings.PAGE_SIZE:
        args[-1] = page_index + 1
        next_url = reverse(url_name, args=args) + qs
        
    return prev_url, next_url
    
