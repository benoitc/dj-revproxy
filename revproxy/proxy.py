# -*- coding: utf-8 -
#
# This file is part of dj-revproxy released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement
import uuid

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect
import restkit
from restkit.globals import set_manager
from restkit.manager import Manager

      	
_hop_headers = {
    'connection':1, 'keep-alive':1, 'proxy-authenticate':1,
    'proxy-authorization':1, 'te':1, 'trailers':1, 'transfer-encoding':1,
    'upgrade':1
}

def is_hop_by_hop(header_name):
    """Return true if 'header_name' is an HTTP/1.1 "Hop-by-Hop" header"""
    return header_name.lower() in _hop_headers

restkit.set_logging("debug")

from .util import absolute_uri, header_name, coerce_put_post, \
rewrite_location, import_conn_manager, absolute_uri
from .filters import RewriteBase
from .store import RequestStore

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
def proxy_request(request, **kwargs):
    """ generic view to proxy a request.

    Args:

        destination: string, the proxied url
        prefix: string, the prrefix behind we proxy the path
        headers: dict, custom HTTP headers
        no_redirect: boolean, False by default, do not redirect to "/" 
            if no path is given
        decompress: boolean, False by default. If true the proxy will
            decompress the source body if it's gzip encoded.
        filters: list of revproxy.Filter instance

    Return:

        HttpResponse instance
    """

    # proxy sid
    try:
        cookie_name = settings.REVPROXY_COOKIE
    except AttributeError:
        cookie_name = kwargs.get("cookie", "PROXY_SID")

    sid = request.COOKIES.get(cookie_name)

    # create a proxy session id only if it's needed so someone using
    # a cookie based authentification can just reuse this session id.
    # It can also be the session id from the session middleware.
    if not sid:
        sid = uuid.uuid4().hex
    kwargs['proxy_sid'] = sid

    
    # install request filters
    filters_classes = kwargs.get('filters')
    if not filters_classes:
        filters = None 
    else:
        filters = []
        for fclass in filters_classes:
            # add filter instance
            fobj = fclass(request, **kwargs)
            filters.append(fobj)

            # eventually rewrite request and kwargs
            if hasattr(fobj, 'setup'):
                ret = fobj.setup()
                if ret is not None:
                    try:
                        request, extra_kwargs = ret
                    except ValueError:
                        extra_kwargs = ret

                    if extra_kwargs is not None:
                        kwargs.update(extra_kwargs)
    

    destination = kwargs.get('destination')
    prefix = kwargs.get('prefix')
    headers = kwargs.get('headers')
    no_redirect = kwargs.get('no_redirect', False)
    decompress = kwargs.get("decompress", False)
    path = kwargs.get("path")
    proxy_sid = kwargs.get('proxy_sid')

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

    # fix headers@
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

    # django doesn't understand PUT sadly
    method = request.method.upper()
    if method == "PUT":
        coerce_put_post(request)
       
    # do the request
    try:
        resp = restkit.request(proxied_url, method=method,
                body=request.raw_post_data, headers=headers,
                follow_redirect=True,
                decompress=decompress,
                filters=filters)
    except restkit.RequestFailed, e:
        msg = getattr(e, 'msg', '')
    
        if e.status_int >= 100:
            resp = e.response
            body = msg
        else:
            return http.HttpResponseBadRequest(msg)

    body =  resp.tee()
    response = HttpResponse(body, status=resp.status_int)


    # fix response headers
    for k, v in resp.headers.items():
        kl = k.lower()
        if is_hop_by_hop(kl):
            continue
        if kl  == "location":
            response[k] = rewrite_location(request, prefix, v)
        elif kl == "content-encoding":
            if not decompress:
                response[k] = v
        else:
            response[k] = v
    
    # save the session 
    response.set_cookie(
            cookie_name, 
            sid,
            max_age=None,
            expires=None,
            domain=settings.SESSION_COOKIE_DOMAIN,
            path=settings.SESSION_COOKIE_PATH,
            secure=True)

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
