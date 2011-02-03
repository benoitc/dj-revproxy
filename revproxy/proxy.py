# -*- coding: utf-8 -
#
# This file is part of dj-revproxy released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement
import uuid

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.servers.basehttp import is_hop_by_hop
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect
import restkit
from restkit.globals import set_manager
from restkit.manager import Manager


restkit.set_logging("debug")

from revproxy.util import absolute_uri, header_name, coerce_put_post, \
rewrite_location, import_conn_manager

_conn_manager = None
def set_conn_manager():
    global _conn_manager

    nb_connections = getattr(settings, 'REVPROXY_NB_CONNECTIONS', 10)
    timeout = getattr(settings, 'REVPROXY_TIMEOUT', 150)

    
    conn_manager_uri = getattr(settings, 'REVPROXY_CONN_MGR', None)
    if not conn_manager_uri:
        
        klass = Manager
    else:
        klass = import_conn_manager(conn_manager_uri)
    _conn_manager = klass(max_conn=nb_connections, timeout=timeout)

def get_conn_manager():
    global _conn_manager
    if not _conn_manager:
        set_conn_manager()
    return _conn_manager


class HttpResponseBadGateway(HttpResponse):
    status_code = 502



@csrf_exempt
def proxy_request(request, destination=None, prefix=None, headers=None,
        no_redirect=False, decompress=True, **kwargs):
    """ generic view to proxy a request.

    Args:

        destination: string, the proxied url
        prefix: string, the prrefix behind we proxy the path
        headers: dict, custom HTTP headers
        no_redirect: boolean, False by default, do not redirect to "/" 
            if no path is given
        decompress: boolean, False by default. If true the proxy will
            decompress the source body if it's gzip encoded.

    Return:

        HttpResponse instance
    """

    path = kwargs.get("path")

    if path is None:
        path = request.path
        if prefix is not None and prefix:
            path = path.split(prefix, 1)[1]
    else:
        if not path and not request.path.endswith("/"):
            if not no_redirect:
                qs = request.META["QUERY_STRING"]
                redirect_url = "%s/" % request.path
                if qs:
                    redirect_url = "%s?%s" % (redirect_url, qs)
                return HttpResponsePermanentRedirect(redirect_url)

        if path:
            prefix = request.path.rsplit(path, 1)[0]

    if not path.startswith("/"):
        path = "/%s" % path 

    base_url = absolute_uri(request, destination)
    proxied_url = ""
    if not path:
        proxied_url = "%s/" % base_url
    else:
        proxied_url = "%s%s" % (base_url, path)

    qs = request.META.get("QUERY_STRING")
    if qs is not None and qs:
        proxied_url = "%s?%s" % (proxied_url, qs)

    # fix headers
    headers = headers or {}
    for key, value in request.META.iteritems():
        if key.startswith('HTTP_'):
            key = header_name(key)
            
        elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            key = key.replace('_', '-')
            if not value: continue
        else:
            continue
    
        # rewrite location
        if key.lower() != "host" and not is_hop_by_hop(key):
            headers[key] = value

    # we forward for
    headers["X-Forwarded-For"] = request.get_host()

    # used in request session store.
    headers["X-Restkit-Reqid"] = uuid.uuid4().hex

    del headers['Accept-Encoding']

    # django doesn't understand PUT sadly
    method = request.method.upper()
    if method == "PUT":
        coerce_put_post(request)

    # do the request


    try:
        resp = restkit.request(proxied_url, method=method,
                body=request.raw_post_data, headers=headers,
                follow_redirect=True,
                decompress=decompress)
    except restkit.RequestFailed, e:
        msg = getattr(e, 'msg', '')
    
        if e.status_int >= 100:
            resp = e.response
            body = msg
        else:
            return http.HttpResponseBadRequest(msg)

    print type(resp._body)

    with resp.body_stream() as body:
        response = HttpResponse(body, status=resp.status_int)

        # fix response headers
        for k, v in resp.headers.items():
            kl = k.lower()
            if is_hop_by_hop(kl):
                continue
            if kl  == "location":
                response[k] = rewrite_location(request, prefix, v)
                print v
                print response[k]
            else:
                response[k] = v

        return response


class ProxyTarget(object):

    def __init__(self, prefix, url, kwargs=None):
        if not prefix or not url:
            raise ValueError("REVPROXY_SETTINGS is invalid")
        if url.endswith("/"):
            url = url[:-1]

        self.prefix = prefix
        self.url = url
        self.kwargs = kwargs or {}

    def __repr__(self):
        return "<%s [%s = %s]>" % (self.__class__.__name__, self.prefix,
                self.url)

class RevProxy(object):

    def __init__(self, name=None, app_name='revproxy'):
        self.name = name or 'revproxy'
        self.app_name = app_name
        self._proxied_urls = None

    def get_proxied_urls(self):
        if self._proxied_urls is None:
            REVPROXY_SETTINGS = getattr(settings, "REVPROXY_SETTINGS", [])
            self._proxied_urls = {}
            for target in REVPROXY_SETTINGS:
                target_inst = ProxyTarget(*target)
                self._proxied_urls[target_inst.prefix] = target_inst
        return self._proxied_urls

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url, include
        urlpatterns = patterns('')
        proxied_urls = self.get_proxied_urls()
        for prefix, target in proxied_urls.items():
            urlpatterns += patterns('',
                url(r"^%s(?P<path>.*)$" % prefix, self, {'prefix': prefix}))
        return urlpatterns

    def urls(self):
        return self.get_urls(), self.app_name, self.name
    urls = property(urls)


    def __call__(self, request, *args, **kwargs):
        headers = {}
        prefix = kwargs.pop('prefix', None)
        path = kwargs.get("path")
        proxied_urls = self.get_proxied_urls()

        if prefix is None or prefix not in proxied_urls:
            return HttpResponseBadGateway("502 Bad Gateway: base url not found")

        if path is None:
            idx =  request.path.find(prefix)
            pos = idx + len(prefix) 
            path = request.path[pos:]
        
        prefix_path = path and request.path.split(path)[0] or request.path
        destination = proxied_urls.get(prefix)
       
        kwargs.update(destination.kwargs)

        return proxy_request(request, destination.url, prefix=prefix_path,
                **kwargs)
        
site_proxy = RevProxy()
