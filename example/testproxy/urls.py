import os

from django.conf.urls.defaults import *

from revproxy import proxy

store_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                        "..", "store"))
print store_path

urlpatterns = patterns('',
    (r'^proxy/', include(proxy.site_proxy.urls)),
    (r'^gunicorn(?P<path>.*)', "revproxy.proxy.proxy_request", {
        "destination": "http://gunicorn.org",
        "decompress": True
    }),
    (r'^google(?P<path>.*)', "revproxy.proxy.proxy_request", {
        "destination": "http://www.google.com",
        "decompress": True,
        "rewrite_base": True,
    }),
    (r'(?P<path>.*)', "revproxy.proxy.proxy_request", {
        "destination": "http://friendpaste.com",
        "store": True,
        "store_path": store_path
    })

)
