"""
Django app of TangleOn main website
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""


from django.contrib.auth.models import AnonymousUser as AuthAnonymousUser
from tangleon.app.models import User

SESSION_KEY = '_tangleon_app_user_session_id'

class AnonymousUser(AuthAnonymousUser):
    """
    This is anonymous user attached to request by middleware
    """
    user_id = -1 # Helps in quering    
    
    def __init__(self):
        self.name = 'Anonymous'
 
    def is_authenticated(self):
        return False
    
    def is_anonymous(self):
        return True

    def get_and_delete_messages(self):
        return []
    
    def is_admin(self):
        return False;
    
    def __str__(self):
        return self.ip;
   
    
class AppMiddleware(object):
    """
    Attaches user object and visit count to every request 
    """
    def process_request(self, request):
        assert hasattr(request, 'session'), "The app authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."                
        try:           
            user_id = request.session[SESSION_KEY]
            try:
                user = User.objects.prefetch_related('fbuser_set').get(user_id=user_id)
                fbusers = user.fbuser_set.all()[:1]
                if fbusers:
                    user.fbuser = fbusers[0]
                    user.fb_id = fbusers[0].fb_id

                request.app_user = user if user.is_active else AnonymousUser()                 
            except User.DoesNotExist:
                request.app_user = AnonymousUser()
        except KeyError:
            request.app_user = AnonymousUser()
        
        try:
            request.visits = int(request.COOKIES['visits']) if 'visits' in request.COOKIES else 0
        except:
            request.visits = 0
                    
        request.app_user.ip = request.META.get('REMOTE_ADDR', 'unknown')
        return None
    
    def process_response(self, request, response):
        """
        Set visits count in cookie
        """            
        response.set_cookie('visits', 0)#request.visits + 1)
        
        return response

    
def login_user(request, user):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request.
    """
    # TODO: It would be nice to support different login methods, like signed cookies.
 
    request.session[SESSION_KEY] = user.user_id
    user.login()
    #if hasattr(request, 'user'):
    request.app_user = user    


def logout_user(request):
    """
    Removes the authenticated user's ID from the request and flushes their
    session data.
    """
    request.session.flush()
    if hasattr(request, 'app_user'):
        request.app_user = AnonymousUser()
