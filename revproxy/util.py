# -*- coding: utf-8 -
#
# This file is part of dj-revproxy released under the MIT license. 
# See the NOTICE for more information.

import sys

import posixpath
from urlparse import urljoin, urlparse, urlunparse
from django.http import absolute_http_url_re

def absolute_uri(request, base_url):
    if not absolute_http_url_re.match(base_url):
        if base_url.startswith("/"):
            base_url = base_url[1:]

        return '%s://%s/%s' %  (
                request.is_secure() and 'https' or 'http', 
                request.get_host(), base_url)
    return base_url

def normalize(base, url):
    parsed_url = urlparse(urljoin(base,url))
    path = posixpath.normpath(parsed_url[2])
    return urlunparse((parsed_url.scheme, parsed_url.netloc,
            path, parsed_url.params, parsed_url.query, parsed_url.fragment))

def header_name(name):
    """Convert header name like HTTP_XXXX_XXX to Xxxx-Xxx:"""
    words = name[5:].split('_')
    for i in range(len(words)):
        words[i] = words[i][0].upper() + words[i][1:].lower()
        
    result = '-'.join(words)
    return result


def coerce_put_post(request):
    """
    Django doesn't particularly understand REST.
    In case we send data over PUT, Django won't
    actually look at the data and load it. We need
    to twist its arm here.
    The try/except abominiation here is due to a bug
    in mod_python. This should fix it.
    Function from django-piston project.
    """
    if request.method == "PUT":
        try:
            request.method = "POST"
            request._load_post_and_files()
            request.method = "PUT"
        except AttributeError:
            request.META['REQUEST_METHOD'] = 'POST'
            request._load_post_and_files()
            request.META['REQUEST_METHOD'] = 'PUT'
            
        request.PUT = request.POST

def rewrite_location(request, prefix_path, location):
    prefix_path = prefix_path or ''
    url = urlparse(location)
    scheme = request.is_secure() and 'https' or 'http'

    if not absolute_http_url_re.match(location):
        # remote server doesn't follow rfc2616
        proxy_uri = '%s://%s%s' % (scheme,
                request.get_host(), prefix_path)
        return  urljoin(proxy_uri, location)
    elif url.scheme == scheme or url.netloc == request.get_host():
        return urlunparse((scheme, request.get_host(), 
            prefix_path + url.path, url.params, url.query, url.fragment))
    return location

def import_conn_manager(module):
    parts = module.rsplit(":", 1)
    if len(parts) == 1:
        raise ImportError("can't import handler '%s'" % module)

    module, obj = parts[0], parts[1]
    try:
        __import__(module)
    except ImportError:
        if module.endswith(".py") and os.path.exists(module):
            raise ImportError("Failed to find manager, did "
                "you mean '%s:%s'?" % (module.rsplit(".",1)[0], obj))
    
    mod = sys.modules[module]
    mgr = eval(obj, mod.__dict__)
    if mgr is None:
        raise ImportError("Failed to find manager object: %r" % mgr)
    return mgr
