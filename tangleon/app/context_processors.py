"""
Context processors for tangleon
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""

import datetime

from django.conf import settings

from tangleon.app.forms import SignUp
from tangleon.app.models import Tag, Channel


def bootstrip(request):
    """
    Setting basic context variables
    """
    user_messages = None
    new_messages = None
    last_message_id = None
    signup_form = None
    followings = None
    
    if request.app_user.is_authenticated():
        tags = request.app_user.get_tags()
        channels = request.app_user.get_channels()
        user_messages = request.app_user.get_messages()
        followings = request.app_user.get_followings()
        new_messages = len([msg for msg in user_messages if msg.viewed_on == None])
        last_message_id = max(user_messages, key=lambda msg: msg.message_id).message_id if len(user_messages) else None
    else:
        tags = Tag.get_tags()
        channels = Channel.get_channels()
        signup_form = SignUp()
        
    return {
            'app_user': request.app_user,
            'tags': tags,
            'channels': channels,
            'user_messages': user_messages,
            'new_messages': new_messages,
            'last_message_id': last_message_id,
            'followings': followings,            
            'signup_form': signup_form,
            'utc_now': datetime.datetime.now(),
            'STATIC_CONTENT_VERSION': settings.STATIC_CONTENT_VERSION
            }
