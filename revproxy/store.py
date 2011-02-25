# -*- coding: utf-8 -
#
# This file is part of dj-revproxy released under the MIT license. 
# See the NOTICE for more information.
import os
import types
import uuid
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from restkit.tee import TeeInput, ResponseTeeInput
from restkit.client import USER_AGENT

from .filters import Filter

class RequestBodyWrapper(TeeInput):

    def __init__(self, request, fobject):
        self.fobject = fobject

        super(RequestBodyWrapper, self).__init__(request.body)
               
    def _tee(self, length):
        data = super(RequestBodyWrapper, self)._tee(length)
        if not data:
            return data
        self.fobject.write(data)

        return data

    def _finalize(self):
        self.fobject.close()
        return super(RequestBodyWrapper, self)._finalize()

class ResponseBodyWrapper(ResponseTeeInput):

    def __init__(self, response, fobject):
        self.fobject = fobject

        super(ResponseBodyWrapper, self).__init__(response, 
                response.connection, response.should_close)
    
    def _tee(self, length):
        data = super(ResponseBodyWrapper, self)._tee(length)
        if not data:
            return data
        self.fobject.write(data)

        return data

    def _finalize(self):
        self.fobject.close()
        return super(ResponseBodyWrapper, self)._finalize()

class RequestStore(Filter):

    def __init__(self, request, **kwargs):
                
        store_path = kwargs.get("store_path", "/tmp")
        request_id = uuid.uuid4().hex

        dirs = os.path.join(*request_id[0:8])
        fdir = os.path.join(store_path, dirs)
        self.fprefix = os.path.join(fdir, request_id[8:])
        if not os.path.exists(fdir):
            os.makedirs(fdir)
        
        self.freq = None
        self.frep = None
        super(RequestStore, self).__init__(request, **kwargs)


    def on_request(self, request):
        self.freq = open("%s.req" % self.fprefix, "w+")
        headers_str = headers_request_str(request)
        self.freq.write(headers_str)
        if request.body is None:
            self.freq.close()
            self.freq = None
        else:
            request.body = RequestBodyWrapper(request,
                    self.freq)
        
    def on_response(self, response, request):
        if self.freq is not None:
            try:
                self.freq.close()
            except OSError:
                pass

        self.frep = open("%s.rep" % self.fprefix, "w+")
        headers_str = headers_response_str(response)
        self.frep.write(headers_str)
        if request.method == "HEAD":
            self.frep.close()
        else:
            response._body = ResponseBodyWrapper(response, 
                    self.frep)

def headers_request_str(request, extra_headers=None):
    """ create final header string """
    headers = request.headers.copy()
    if extra_headers is not None:
        for k, v in extra_headers:
            headers[k] = v

    if not request.body and request.method in ('POST', 'PUT',):
        headers['Content-Length'] = 0

    httpver = "HTTP/1.1"

    ua = headers.iget('user_agent')
    if not ua:
        ua = USER_AGENT 
    host = request.host

    accept_encoding = headers.iget('accept-encoding')
    if not accept_encoding:
        accept_encoding = 'identity'

    lheaders = [
        "%s %s %s\r\n" % (request.method, request.path, httpver),
        "Host: %s\r\n" % host,
        "User-Agent: %s\r\n" % ua,
        "Accept-Encoding: %s\r\n" % accept_encoding
    ]

    lheaders.extend(["%s: %s\r\n" % (k, str(v)) for k, v in \
            headers.items() if k.lower() not in \
            ('user-agent', 'host', 'accept-encoding',)])
    return "%s\r\n" % "".join(lheaders)

def headers_response_str(response):
    version_str = "HTTP/%s.%s" % response.version

    headers = ["%s %s\r\n" % (version_str, response.status)]
    headers.extend(["%s: %s\r\n" % (k, str(v)) for k, v in \
            response.headers.items()])
    return "%s\r\n" % "".join(headers)


