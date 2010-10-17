dj-revproxy
-----------

Django reverse proxy. Allows you to proxy any website behind a prefix.

Requirements
------------

- `Python <http://www.python.org>`_ 2.x superior to 2.5 and Django
- `Django <http://www.djangoproject.org>`_  >= 1.2
- `restkit <http://www.couchdbkit.org>`_ >= 2.1.2

Installation
------------

Install from sources::

  $ python setup.py install

Or from Pypi::

  $ easy_install -U dj-revproxy 

Configuration
-------------

Add `revproxy`  to the list of applications::

    INSTALLED_APPS = (
        ...
        'revproxy'
    )

Usage
-----

Since 0.2, there is 2 ways to use dj-revproxy.


1. Generic view
+++++++++++++++

You can use ``proxy_request`` function to proxy any url. You can use it in your code::

    proxy_request(request, "http://example.com")

This code will proxy current request to ``http://example.com`` domain.
This function can take 5 parameters:

- destination: string, the proxied url. Required
- path: string, If no path is given it will try to detect the url using
  the prefix if it's given. If not full request.path will be used in
  finl destination url.
- prefix: string, the prrefix behind we proxy the path
  headers: dict, custom HTTP headers
- no_redirect: boolean, False by default, do not redirect to "/" 
  if no path is given
- decompress: boolean, False by default. If true the proxy will
  decompress the source body if it's gzip encoded.

It return an instance of ``django.http.HttpResponse``. You can use it  directly
in your urls.py (which is the eaiest way to use). Ex::

    (r'^gunicorn(?P<path>.*)', "revproxy.proxy_request", {
        "destination": "http://gunicorn.org"
    }),

2. Configure multiple proxy behind one generic prefix
+++++++++++++++++++++++++++++++++++++++++++++++++++++

To configure a proxy add a tupple to the REVPROXY_SETTINGS list::

    REVPROXY_SETTINGS = [
        ("_google", "http://google.com"),
        ("_friendpaste", "http://www.friendpaste.com"),
        ("_couchdb", "http://127.0.0.1:5984"),
    ]

Then configure your proxied urls automatically do something like this in
``urls.py``:: 
    from django.conf.urls.defaults import *

    import revproxy

    urlpatterns = patterns('',
        ...
        (r'^proxy/', include(revproxy.site_proxy.urls)),
    )

Which will allow you to proxy Google on the url::

    http://127.0.0.1:8000/proxy/_google

or even::

    ('^proxy/(?P<prefix>[^\/]*)(.*)', "revproxy.site_proxy"),

