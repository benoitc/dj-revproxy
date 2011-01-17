from django.conf.urls.defaults import *

from revproxy import proxy

urlpatterns = patterns('',
    (r'^proxy/', include(proxy.site_proxy.urls)),
    (r'^gunicorn(?P<path>.*)', "revproxy.proxy.proxy_request", {
        "destination": "http://gunicorn.org"
    }),
    (r'(?P<path>.*)', "revproxy.proxy.proxy_request", {
        "destination": "http://friendpaste.com"
    })

)
