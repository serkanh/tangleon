"""
TangleOn basic classes
@author: faraz@tangleon.com
@copyright: Copyright (c) 2014 TangleOn
"""


class TangleOnError(Exception):    
    def __init__(self, message):                
        self.message = message