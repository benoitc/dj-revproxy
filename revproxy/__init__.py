# -*- coding: utf-8 -
#
# This file is part of dj-revproxy released under the MIT license. 
# See the NOTICE for more information.

version_info = (0, 3, 0)
__version__ =  ".".join(map(str, version_info))

try:
    from revproxy.proxy import proxy_request, RevProxy, site_proxy
except ImportError:
    import traceback
    traceback.print_exc()
