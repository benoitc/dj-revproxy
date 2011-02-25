# -*- coding: utf-8 -
#
# This file is part of dj-revproxy released under the MIT license. 
# See the NOTICE for more information.

# etree object

import posixpath
import urlparse
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


from django.http import absolute_http_url_re
try:
    from lxml import etree
    import lxml.html
except ImportError:
    raise ImportError("""lxml isn't installed

        pip installl lxml
""")

from revproxy.util import normalize

HTML_CTYPES = ( 
    "text/html",
    "application/xhtml+xml",
    "application/xml"
)


class Filter(object):
    """ Filter Interface """

    def __init__(self, request, **kwargs):
        self.request = request
        self.kwargs = kwargs

    def setup(self):
        """ used to update request options. Return None or a dict
        instance"""
        return None


class RewriteBase(Filter):

    def __init__(self, request, **kwargs):
        self.absolute_path = '%s://%s%s' %  (
                request.is_secure() and 'https' or 'http', 
                request.get_host(), 
                request.path)
        super(RewriteBase, self).__init__(request, **kwargs)

    def setup(self):
        return {'decompress': True}
        
    def rewrite_link(self, link):
        if not absolute_http_url_re.match(link):
            if link.startswith("/"):
                link = link[1:]

            absolute_path = self.absolute_path 
            if self.absolute_path.endswith("/"):
                absolute_path = absolute_path[1:]

            return normalize(absolute_path, link) 
        return link

    def on_response(self, resp, req):
        ctype = resp.headers.iget('content-type')
        if not ctype:
            return

        ctype = ctype.split(";", 1)[0]

        # if this is an html page, parse it
        if ctype in HTML_CTYPES:
            body = resp.body_string()
           
            html = lxml.html.fromstring(body)

            # rewrite links to absolute 
            html.rewrite_links(self.rewrite_link)

            # add base
            old_base = html.find(".//base")
            base = etree.Element("base")
            base.attrib['href'] = self.absolute_path 

            if not old_base:
                head = html.find(".//head")
                head.append(base)
            
            # modify response
            rewritten_body = lxml.html.tostring(html)
            try:
                resp.headers.ipop('content-length')
            except KeyError:
                pass

            resp.headers['Content-Length'] = str(len(rewritten_body))
            resp._body = StringIO(rewritten_body)
            resp._already_read = False


