from collections import OrderedDict
from datetime import datetime, timedelta
from utils.config import CACHE

class Cache:
    def __init__(self):
        self.cache = OrderedDict()
        self.timeout = CACHE['timeout']
        self.max_size = CACHE['max_size']
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.timeout):
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[key] = (value, datetime.now())