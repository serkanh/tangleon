"""
Utility methods for TangleOn
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""

import re
import urllib
import urllib2
import httplib
import urlparse
import HTMLParser

from tangleon import TangleOnError

META_REGEX = r'''<meta[^>]*(?:property\s*=\s*"\s*{property}\s*"[^>]*content\s*=\s*(?:'|")([^"\r\n]+)(?:'|")[^>]*|content\s*=\s*(?:'|")([^"\r\n]+)(?:'|")[^>]*property\s*=\s*"\s*{property}\s*"[^>]*)>'''
LINK_REGEX = r'''<link[^>]*(?:rel\s*=\s*"[^"]*{rel}[^"]*"[^>]*href\s*=\s*"([^"\r\n]+)"[^>]*|href\s*=\s*"([^"\r\n]+)"[^>]*rel\s*=\s*"[^"]*{rel}[^"]*"[^>]*)>'''

IMG_SRC_REGEX = re.compile(r'<img[^>]*src\s*=\s*"([^"\r\n]+)"[^>]*>', re.IGNORECASE)
IMG_ALT_REGEX = re.compile(r'<img[^>]*alt\s*=\s*"([^"\r\n]+)"[^>]*>', re.IGNORECASE)
TITLE_REGEX = re.compile(r'<title\s*>([^<]+)</\s*title\s*>', re.IGNORECASE)    
ICON_REGEX = re.compile(LINK_REGEX.format(rel='icon'), re.IGNORECASE)
DESCRIPTION_REGEX = re.compile(r'<meta[^>]*name\s*=\s*"\s*description\s*"[^>]*content\s*=\s*"([^"\r\n]+)"[^>]*>', re.IGNORECASE)
OG_URL_REGEX = re.compile(META_REGEX.format(property='og:url'), re.IGNORECASE)
OG_TITLE_REGEX = re.compile(META_REGEX.format(property='og:title'), re.IGNORECASE)
OG_DESCRIPTION_REGEX = re.compile(META_REGEX.format(property='og:description'), re.IGNORECASE)
OG_IMAGE_REGEX = re.compile(META_REGEX.format(property='og:image'), re.IGNORECASE)
OG_VIDEO_REGEX = re.compile(META_REGEX.format(property='og:video'), re.IGNORECASE)
OG_VIDEO_TYPE_REGEX = re.compile(META_REGEX.format(property='og:video:type'), re.IGNORECASE)
LINK_IMAGE_SRC_REGEX = re.compile(LINK_REGEX.format(rel='image_src'), re.IGNORECASE)
LINK_VIDEO_SRC_REGEX = re.compile(LINK_REGEX.format(rel='video_src'), re.IGNORECASE)
LINK_VIDEO_TYPE_REGEX = re.compile(LINK_REGEX.format(rel='video_type'), re.IGNORECASE)
HTML_PARSER = HTMLParser.HTMLParser()

def get_page_title(url):
    """
    Returns page title from og:title meta tag or title tag
    """
    content_type, content = get_page_content(url)
    
    if content_type.startswith('image/'):
        raise TangleOnError('It is an image url, please suggest title by yourself')
    
    if content_type != 'text/html':
        raise TangleOnError('Content at url is not html, please suggest title by yourself')
        
    title = get_value(OG_TITLE_REGEX, content) or get_value(TITLE_REGEX, content)
    if title:
        return HTML_PARSER.unescape(title)
    
    raise TangleOnError('Page title doesn\'t exists in the web page.') 


def get_media_tags(url):
    """
    Returns dict of image and video urls if defined for page in meta tags
    
    tags => image, video, video_type
    """
    content_type, content = get_page_content(url)
    
    tags = {}
    
    if content_type.startswith('image/'):
        tags['image'] = url
        return tags
    
    if content_type.startswith('video/') or content_type == 'application/x-shockware-flash':
        tags['video'] = url
        tags['video_type'] = content_type
        return tags
    
    img_url = get_value(LINK_IMAGE_SRC_REGEX, content) or get_value(OG_IMAGE_REGEX, content)    
    
    # Removing width or height parameters in query string to get maximum image size    
    if img_url:                  
        url_parts = list(urlparse.urlparse(img_url))
        
        qs = dict(urlparse.parse_qsl(url_parts[4]))
        qs.pop('w', None)
        qs.pop('h', None)
        qs.pop('width', None)
        qs.pop('height', None)
        qs.pop('size', None)
        
        url_parts[4] = urllib.urlencode(qs)
        tags['image'] = urlparse.urlunparse(url_parts)
    
    video = get_value(LINK_VIDEO_SRC_REGEX, content) or get_value(OG_VIDEO_REGEX, content)
    if video:
        tags['video'] = video
        tags['video_type'] = get_value(LINK_VIDEO_TYPE_REGEX, content) or get_value(OG_VIDEO_TYPE_REGEX, content) or 'application/x-shockwave-flash'
        
    return tags


def get_icon_url_and_description(link, feed):
    """
    Return icon url and description if found on the link
    """
    icon_url = None
    description = None
    content_type, content = get_page_content(link)
    
    if content_type == 'text/html':        
        icon_url = get_value(ICON_REGEX, content)        
        description = get_value(DESCRIPTION_REGEX, content) or get_value(DESCRIPTION_REGEX, content)
        
        if not icon_url and hasattr(feed, 'image') and hasattr(feed.image, 'href'):    
            icon_url = feed.image.href
            
        if not description  and hasattr(feed, 'description'):
            description = feed.description
            
    return icon_url, description


def get_page_content(url):
    """
    Returns page content on specified url
    """
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) tangleon.com +(mailto:hi@tangleon.com)')
    
    try:
        response = urllib2.urlopen(request)
        try:
            content_type = response.info().type
            if content_type.startswith('text/'):
                return content_type, response.read()
            
            return content_type, None
        finally:
            response.close()
    except (urllib2.URLError, httplib.BadStatusLine):
        raise TangleOnError('Url doesn\'t seems to be a accessible, we can\'t open it.')


def get_content(url):
    """
    Returns page content on specified url
    """
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) tangleon.com +(mailto:hi@tangleon.com)')
        
    response = urllib2.urlopen(request)
    try:
        return response.read()
    finally:
        response.close()    
            

def get_img_url_from_entry(entry):
    """
    Returns first image (.jpg or .png) url found in RSS item description
    """
    content = get_content_from_entry(entry)
    img_url = get_value(IMG_SRC_REGEX, content)    
    if img_url.endswith('.jpg') or '.jpg?' in img_url or img_url.endswith('.png') or '.png?' in img_url:
        return img_url
        
    return None


def get_img_alt_from_entry(entry):
    """
    Returns first image alt from RSS item description
    """
    content = get_content_from_entry(entry)
    return get_value(IMG_ALT_REGEX, content)
    
    
def get_content_from_entry(entry):
    """
    Returns best xhtml content of RSS item entry
    """
    contents = entry.get('content', None)
    if contents:
        for content in contents:
            if content.type == 'application/xhtml+xml':
                return content.value
            
        for content in contents:
            if content.type == 'text/html':
                return content.value                 

        return contents[0].value
    
    return entry.summary

def get_value(regex, content):
    """
    Returns not null value that matches regex expression
    """
    match = regex.search(content)
    if match:
        for value in match.groups():
            if value:
                return value.strip()
    
    return None