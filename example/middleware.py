from django.conf import settings
from django.contrib.sites.models import Site

class CurrentSiteMiddleware(object):
    def process_request(self, request):
        site = Site.objects.get(id=settings.SITE_ID)
        if site.domain != request.get_host():
            site.domain = request.get_host()
            site.save()
