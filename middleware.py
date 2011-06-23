# -*- coding: utf-8 -*-

import re
from django.http import HttpResponsePermanentRedirect
from django.conf import settings

class UrlRedirectMiddleware:
    def process_request(self, request):
        host = request.META['PATH_INFO']
        for url_pattern, redirect_url in settings.URL_REDIRECTS:
            regex = re.compile(url_pattern)
            if regex.match(host):
                return HttpResponsePermanentRedirect(redirect_url)