from django.conf.urls.defaults import *

import revproxy

urlpatterns = patterns('',
    (r'^proxy/', include(revproxy.site_proxy.urls)),
    (r'^(?P<path>.*)', "revproxy.site_proxy", {"prefix":
        "_friendpaste"}),
    
)
