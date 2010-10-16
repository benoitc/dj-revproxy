# -*- coding: utf-8 -
#
# This file is part of dj-revproxy released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

from django.conf import settings
from django.core.servers.basehttp import is_hop_by_hop
from django.http import HttpResponse, Http404 
import restkit

from revproxy.util import absolute_uri, header_name, coerce_put_post, \
rewrite_location

# define HTTP connection pool
REVPROXY_POOL = restkit.SimplePool()


class HttpResponseBadGateway(HttpResponse):
    status_code = 502

class BodyWrapper(object):

    def __init__(self, body):
        self.body = body

    def __iter__(self):
        return self

    def next(self):
        ret = self.body.readline()
        if not ret:
            raise StopIteration()
        return ret

class RevProxy(object):

    def __init__(self, name=None, app_name='revproxy'):
        self.name = name or 'revproxy'
        self.app_name = app_name
        self._proxied_urls = None

    def get_proxied_urls(self):
        from django.conf import settings
        if self._proxied_urls is None:
            REVPROXY_SETTINGS = getattr(settings, "REVPROXY_SETTINGS", [])
            self._proxied_urls = {}
            for prefix, base_url in REVPROXY_SETTINGS:
                if not prefix or not base_url:
                    raise ValueError("REVPROXY_SETTINGS is invalid")

                if base_url.endswith("/"):
                    base_url = base_url[:-1]
                self._proxied_urls[prefix] = base_url
        return self._proxied_urls

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url, include
        urlpatterns = patterns('')
        proxied_urls = self.get_proxied_urls()
        for prefix, base_url in proxied_urls.items():
            urlpatterns += patterns('',
                url(r"^%s(?P<path>.*)$" % prefix, self, {'prefix': prefix}))
        return urlpatterns

    def urls(self):
        return self.get_urls(), self.app_name, self.name
    urls = property(urls)


    def __call__(self, request, *args, **kwargs):
        headers = {}
        prefix = kwargs.get('prefix')
        path = kwargs.get("path")
        proxied_urls = self.get_proxied_urls()

        if prefix is None or prefix not in proxied_urls:
            return HttpResponseBadGateway("502 Bad Gateway: base url not found")

        if path is None:
            idx =  request.path.find(prefix)
            pos = idx + len(prefix) 
            path = request.path[pos:]

        if not path.startswith("/"):
            path = "/%s" % path

        base_url = absolute_uri(request, proxied_urls.get(prefix))
        prefix_path = path and request.path.split(path) or ''
        # build proxied_url
        proxied_url = ""
        if not path:
            proxied_url = base_url
        else:
            proxied_url = "%s%s" % (base_url, path)

        # fix headers
        headers = {}
        for key, value in request.META.iteritems():
            if key.startswith('HTTP_'):
                key = header_name(key)
                
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                key = key.replace('_', '-')
                if not value: continue
            else:
                continue
        
            # rewrite location
            if key.lower() == "host":
                continue
            if is_hop_by_hop(key):
                continue
            else:
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
                    decompress=False,
                    pool_instance=REVPROXY_POOL)
        except restkit.RequestFailed, e:
            msg = getattr(e, 'msg', '')
        
            if e.status_int >= 100:
                resp = e.response
                body = msg
            else:
                return http.HttpResponseBadRequest(msg)

        with resp.body_stream() as body:
            response = HttpResponse(BodyWrapper(body), status=resp.status_int)

            # fix response headers
            for k, v in resp.headers.items():
                kl = k.lower()
                if is_hop_by_hop(kl):
                    continue
                if kl  == "location":
                    response[k] = rewrite_location(request, prefix_path,
                            v)
                #elif kl == "content-encoding":
                #    continue
                else:
                    response[k] = v
            return response

site_proxy = RevProxy()
