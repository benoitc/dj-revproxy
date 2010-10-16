dj-revproxy
-----------

Django reverse proxy. Allows you to proxy any wabsite behind a prefix.

Requirements
------------

- `Python <http://www.python.org>`_ 2.x superior to 2.5 and Django
- `Django <http://www.djangoproject.org>`_  >= 1.2
- `restkit <http://www.couchdbkit.org>`_ >= 2.1.1 

Installation
------------

Add `revproxy`  to the list of applications::

    INSTALLED_APPS = (
        ...
        'revproxy'
    )

To configure a proxy add a tupple to the REVPROXY_SETTINGS list::

    REVPROXY_SETTINGS = [
        ("_google", "http://google.com"),
        ("_friendpaste", "http://www.friendpaste.com"),
        ("_couchdb", "http://127.0.0.1:5984"),
    ]

The configure your urls to add revproxy to the list::

    from django.conf.urls.defaults import *

    import revproxy

    urlpatterns = patterns('',
        ...
        (r'^proxy/', include(revproxy.site_proxy.urls)),
    )

Which will allow you to proxy Google on the url::

    http://127.0.0.1:8000/proxy/_google


