from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

#from django.contrib import admin
#admin.autodiscover()

from wikiprox.sitemaps import MediaWikiSitemap, SourceSitemap
sitemaps = {
    'wiki': MediaWikiSitemap,
    'sources': SourceSitemap,
}

urlpatterns = patterns(
    '',
    #url(r'^admin/', include(admin.site.urls)),
    url(r'^crossdomain\.xml$', direct_to_template, {'template': 'crossdomain.xml'}),
    url(r'^qr/$', direct_to_template, {'template': 'qr.html'}, name='qr'),
    url(r'^robots\.txt$', direct_to_template, {'template': 'robots.txt'}),
    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    #
    url(r'^videotest/$', direct_to_template, {'template': 'wikiprox/LVplusJWPlayer.html'}),
    #
    url(r'^about/editorsmessage/embed/$', direct_to_template, {'template': 'editorsmessage-lightbox.html'}, name='editorsmessageembed'),
    url(r'^about/editorsmessage/$', direct_to_template, {'template': 'editorsmessage.html'}, name='editorsmessage'),
    url(r'^about/$', direct_to_template, {'template': 'about.html'}, name='about'),
    url(r'^authors/$', 'wikiprox.views.authors', name='wikiprox-authors'),
    url(r'^categories/$', 'wikiprox.views.categories', name='wikiprox-categories'),
    url(r'^contents/$', 'wikiprox.views.contents', name='wikiprox-contents'),
    url(r'^history/$', direct_to_template, {'template': 'history.html'}),
    url(r'^search/$', direct_to_template, {'template': 'search.html'}),
    url(r'^terminology/$', direct_to_template, {'template': 'terminology.html'}),
    #
    url(r'^timeline/$', 'events.views.events', name='events-events'),
    #
    url(r'^locations-(?P<category>[\w]+).kml$', 'locations.views.locations_kml', name='locations-kml-category'),
    url(r'^locations.kml$', 'locations.views.locations_kml', name='locations-kml'),
    url(r'^map/(?P<category>[\w]+)/$', 'locations.views.locations', name='locations-category'),
    url(r'^map/$', 'locations.views.locations', name='locations-index'),
    #
    url(r"^sources/(?P<encyclopedia_id>[\w .:_-]+)/$", 'wikiprox.views.source', name='wikiprox-source'),
    #
    # temp cite functionality patch 2013-03-26 gf
    url(r'^citehelp/$', direct_to_template, {'template': 'citehelp.html'}, name='citehelp'),
    #
    url(r"^cite/source/(?P<encyclopedia_id>[\w .:_-]+)/$", 'wikiprox.views.source_cite', name='wikiprox-source-cite'),
    url(r"^cite/page/(?P<url_title>[\w\W]+)/$", 'wikiprox.views.page_cite', name='wikiprox-page-cite'),
    #
    url(r"^print/(?P<url_title>[\w\W]+)/$", 'wikiprox.views.page', {'printed':True}, name='wikiprox-page-print'),
    url(r"^(?P<url_title>[\w\W]+)/$", 'wikiprox.views.page', name='wikiprox-page'),
    url(r"^$", 'wikiprox.views.index', name='wikiprox-index'),
)
