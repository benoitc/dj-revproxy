# -*- coding: utf-8 -
#
# This file is part of dj-revproxy released under the MIT license. 
# See the NOTICE for more information.

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
    url = urlparse(location)
    source = url.parse(request.get_host)

    if not absolute_http_url_re.match(location):
        # remote server doesn't follow rfc2616
        proxy_uri = '%s://%s%s' % (
                request.is_secure() and 'https' or 'http',
                request.get_host(), prefix_path)

        return  urljoin(proxy_uri, location)
    
    elif url.scheme != source.scheme or url.netloc != source.netloc:
        url.path = prefix_path + url.path
        return urlunparse((source.scheme, source.netloc,
            prefix_path+url.path, url.params, url.query, url.fragment))

    return location




