"""
Tags for generating preview image
"""

import urllib
from django import template
 
register = template.Library()
 
class PreviewImageNode(template.Node):
    def __init__(self, img_url, width, height):
        self.img_url = template.Variable(img_url)
        self.width = template.Variable(width)
        self.height = template.Variable(height)
 
    def render(self, context):
        try:
            img_url = self.img_url.resolve(context)
        except template.VariableDoesNotExist:
            return ''
        
        try:
            width = self.width.resolve(context)
        except template.VariableDoesNotExist:
            return ''
        
        try:
            height = self.height.resolve(context)
        except template.VariableDoesNotExist:
            return ''
                
        if img_url:
            if img_url.startswith('http://'):
                preview_img_url = img_url[7:]
            elif img_url.startswith('https://'):
                preview_img_url = 'ssl:' +  img_url[8:]
            elif img_url.startswith('//'):
                preview_img_url = img_url[2:]
            else:
                preview_img_url = img_url
                    
            return u'http://images.weserv.nl/?' + urllib.urlencode({'url': unicode(preview_img_url).encode('utf-8'), 'w': width, 'h': height, 't': 'square'})
        
        return ''

 
@register.tag
def preview_img_url(parser, token):
    
    tokens = token.split_contents()
    
    if len(tokens) == 4:
        tag_name, img_url, width, height = tokens
        return PreviewImageNode(img_url, width, height)
    
    raise template.TemplateSyntaxError, "%r tag requires a image url, width and height arguments" % token.contents.split()[0]

