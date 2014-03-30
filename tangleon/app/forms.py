"""
Forms
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""

import re
import urllib2

from django import forms

class SignUp(forms.Form):
    """
    User registration form
    """
    username_regex = re.compile('^\w{4,30}$')
    
    username = forms.CharField(max_length=15, error_messages={'required': 'Please choose a username.'})
    email = forms.EmailField(error_messages={'required': 'Please enter your email address.'})
    password = forms.CharField(widget=forms.PasswordInput, min_length=8, error_messages={'required': 'Please enter your password for the website.'})    
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if not self.username_regex.match(username):
            raise forms.ValidationError("Please choose an alphanumeric username of at least 4 characters and not more than 30 characters.")
        return username
    

class PasswordReset(forms.Form):
    """
    Password reset form
    """
    password = forms.CharField(widget=forms.PasswordInput, min_length=8, max_length=50, error_messages={'required': 'Please enter your new password.'})
    confirm_password = forms.CharField(widget=forms.PasswordInput, max_length=50, error_messages={'required': 'Please re-enter your new password for confirmation.'})
    
    def clean_confirm_password(self):
        confirm_password = self.cleaned_data['confirm_password']
        if 'password' in self.cleaned_data and self.cleaned_data['password'] != confirm_password:
            raise forms.ValidationError("Your new password and confirm password didn't matched.")        
        return confirm_password


class ChangePassword(PasswordReset):
    """
    Change password form
    """
    current_password = forms.CharField(widget=forms.PasswordInput, max_length=50, error_messages={'required': 'Please enter your current password.'})



class SubmitPostForm(forms.Form):
    """
    User post submit base form
    """
    title_regex = re.compile(r'[^\w\.]+')
    title = forms.CharField(max_length=250, error_messages={'required': 'Please write title for this post.'})
    tags = forms.CharField(max_length=100, error_messages={'required': 'Please choose at least one tag.'}, help_text='You can choose multiple tags for your post, but choose first tag wisely because it will be considered as a room')
    
    def clean_title(self):
        title = self.cleaned_data['title']
        if len(self.title_regex.split(title)) < 4:
            raise forms.ValidationError("Please write few more words for the title.")
        return title
    
    def clean_tags(self):
        tags = self.cleaned_data['tags']
        return tags.strip(' ,')
    
class SubmitTextPost(SubmitPostForm):
    """
    User text post submit form
    """
    description = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={'cols': 1, 'rows': 8, 'style': 'width:100%;max-width:100%;font-size:0.9em;', 'maxlength': '2000'}))
    

class SubmitLinkPost(SubmitPostForm):
    """
    User link post submit form
    """
    url = forms.URLField(max_length=200, error_messages={'required': 'Please enter Url for web page you want to share.'})
    
    def clean_url(self):
        url = self.cleaned_data['url']        
        req = urllib2.Request(url)        
        if 'tangleon.com' in req.origin_req_host:
            raise forms.ValidationError('Are you sure? that you are posting the right link?')       
        
        return url
