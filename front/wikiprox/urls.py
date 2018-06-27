from django.conf import settings
from django.conf.urls.defaults import *
from django.http import HttpResponseRedirect

from wikiprox import views

urlpatterns = [
    url(r"^index.php/(?P<page>[\w\W]+)/$", views.page, name='wikiprox-page'),
    url(r"^(?P<page>[\w\W]+)/$", views.page, name='wikiprox-page'),
    #
    url(r'^$', lambda x: HttpResponseRedirect('/wiki/%s' % settings.MEDIAWIKI_DEFAULT_PAGE)),
]

# problematic page titles
# period, comma, hyphen, parentheses, slash, single-quote/apostrophe
# Examples:
#   A.L. Wirin
#   Aiko Herzig-Yoshinaga
#   Amache (Granada)
#   Bureau of Sociological Research, Poston
#   Documentary films/videos on incarceration
#   Hawai'i
