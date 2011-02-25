import os

from django.conf.urls.defaults import *

from revproxy import proxy
from revproxy.filters import RewriteBase
from revproxy.store import RequestStore


store_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                        "..", "store"))

urlpatterns = patterns('',
    (r'^proxy/', include(proxy.site_proxy.urls)),
    (r'^gunicorn(?P<path>.*)', "revproxy.proxy.proxy_request", {
        "destination": "http://gunicorn.org",
        "decompress": True
    }),
    (r'^google(?P<path>.*)', "revproxy.proxy.proxy_request", {
        "destination": "http://www.google.com",
        "decompress": True,
        "filters": [RewriteBase]
    }),
    (r'(?P<path>.*)', "revproxy.proxy.proxy_request", {
        "destination": "http://friendpaste.com",
        "store_path": store_path,
        "filters": [RequestStore]
    })

)
