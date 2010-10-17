from django.conf.urls.defaults import *

import revproxy

urlpatterns = patterns('',
    (r'^proxy/', include(revproxy.site_proxy.urls)),
    (r'^gunicorn(?P<path>.*)', "revproxy.proxy_request", {
        "destination": "http://gunicorn.org"
    }),
    (r'(?P<path>.*)', "revproxy.proxy_request", {
        "destination": "http://friendpaste.com"
    })

)
