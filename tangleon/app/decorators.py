"""
Decorators
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""

import urllib

from functools import wraps

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse


def login_required(view_func):
    """
    Decorator for views that checks that the user is logged in or redirect to login page
    """
    @wraps(view_func)
    def check_login(request, *args, **kwargs):        
        if request.app_user.is_authenticated():
            return view_func(request, *args, **kwargs)

        login_url = reverse('app_login') + '?' + urllib.urlencode({'next': request.get_full_path()})
        return HttpResponseRedirect(login_url)
    
    return check_login


def anonymous_required(view_func):
    """
    Decorator for views that checks that the user is not logged.
    """
    @wraps(view_func)
    def check_anonymous(request, *args, **kwargs):
        if request.app_user.is_anonymous():
            return view_func(request, *args, **kwargs)
        
        next = request.GET.get('next', None)        
        return HttpResponseRedirect(next if next else reverse('app_index'))
    
    return check_anonymous
