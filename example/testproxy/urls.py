from django.conf.urls.defaults import *

from revproxy import proxy

from revproxy.filters import RewriteBase

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
        "destination": "http://friendpaste.com"
    })

)
