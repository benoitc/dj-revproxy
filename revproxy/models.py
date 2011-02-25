# -*- coding: utf-8 -
#
# This file is part of dj-revproxy released under the MIT license. 
# See the NOTICE for more information.

from django.contrib import admin
from django.db import models

class RequestSession(models.Model):
    """ simple request session models. All the session is saved on the
    disk """

    sid = models.CharField(max_length=4096)
    executed = models.DateTimeField(auto_now=True)
    request_id = models.CharField(max_length=255)
    store_path = models.CharField(max_length=255)

    def __str__(self):
        return "%s - %s" % (self.executed, self.request_id)

admin.site.register(RequestSession)
