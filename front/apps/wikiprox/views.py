from datetime import datetime, timedelta
import json
import os
import re

from bs4 import BeautifulSoup, SoupStrainer
from bs4 import Comment
import requests

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.views.decorators.http import require_http_methods

from wikiprox import mediawiki as mw
from wikiprox import encyclopedia, sources, citations


@require_http_methods(['GET',])
def index(request, template_name='index.html'):
    return render_to_response(
        template_name,
        {},
        context_instance=RequestContext(request)
    )

@require_http_methods(['GET',])
def page(request, page='index', printed=False, template_name='wikiprox/page.html'):
    """
    """
    url = mw.page_data_url(page)
#    if request.GET.get('pagefrom', None):
#        url = '?'.join([url, 'pagefrom=%s' % request.GET['pagefrom']])
#    elif request.GET.get('pageuntil', None):
#        url = '?'.join([url, 'pageuntil=%s' % request.GET['pageuntil']])
    # request
    r = requests.get(url)
    if r.status_code != 200:
        raise Http404
    pagedata = json.loads(r.text)
    # hide unpublished pages on public systems
    public = request.META.get('HTTP_X_FORWARDED_FOR',False)
    # note: header is added by Nginx, should not appear when connected directly
    # to the app server.
    published = mw.page_is_published(pagedata)
    if (not published) and (not settings.WIKIPROX_SHOW_UNPUBLISHED):
        return render_to_response(
            'wikiprox/unpublished.html',
            {},
            context_instance=RequestContext(request)
        )
    # basic page context
    categories = pagedata['parse']['categories']
    title = pagedata['parse']['displaytitle']
    page_sources_raw = pagedata['parse']['images']
    bodycontent,page_sources = mw.parse_mediawiki_text(
        pagedata['parse']['text']['*'],
        pagedata['parse']['images'],
        public, printed)
    # rewrite media URLs on stage
    # (external URLs not visible to Chrome on Android when connecting through SonicWall)
    if hasattr(settings, 'STAGE') and settings.STAGE:
        page_sources = sources.replace_source_urls(page_sources, request)
    # find coordinates listed in the page, if any
    coordinates_camp = mw.find_databoxcamps_coordinates(pagedata['parse']['text']['*'])
    context = {
        'request': request,
        'page': page,
        'title': title,
        'bodycontent': bodycontent,
        'sources': page_sources,
        'coordinates': coordinates_camp,
        'lastmod': mw.page_lastmod(page),
        'print': printed,
        }
    # author page
    if encyclopedia.is_author(title):
        template_name = 'wikiprox/author.html'
        context.update({
            'author_articles': encyclopedia.author_articles(title),
            })
    # article
    elif encyclopedia.is_article(title):
        if printed:
            template_name = 'wikiprox/article-print.html'
        else:
            template_name = 'wikiprox/article.html'
        context.update({
            'page_categories': encyclopedia.page_categories(title),
            'prev_page': encyclopedia.article_prev(title),
            'next_page': encyclopedia.article_next(title),
            })
    # retsu go!
    return render_to_response(
        template_name, context,
        context_instance=RequestContext(request)
    )

@require_http_methods(['GET',])
def page_cite(request, page=None, template_name='wikiprox/cite.html'):
    page_url = mw.page_data_url(page)
    cite_url = '%s?format=json&action=query&prop=info&prop=revisions&titles=%s' % (settings.WIKIPROX_MEDIAWIKI_API, page)
    r = requests.get(cite_url)
    if r.status_code == 200:
        r_text = r.text
        response = json.loads(r.text)
        keys = response['query']['pages'].keys()
        if len(keys) == 1:
            pageinfo = response['query']['pages'][keys[0]]
            TS_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
            timestamp = pageinfo['revisions'][0]['timestamp']
            lastmod = datetime.strptime(timestamp, TS_FORMAT)
            href = 'http://%s%s' % (request.META['HTTP_HOST'], reverse('wikiprox-page', args=[page]))
            # get author info
            r = requests.get(page_url)
            pagedata = json.loads(r.text)
            authors = mw.find_author_info(pagedata['parse']['text']['*'])
            # For some reason, if next line is added to context with the others,
            # surname and givenname are reversed. Weird.
            authors_cse = citations.format_authors_cse(authors['parsed'])
            return render_to_response(
                template_name,
                {'title': pageinfo['title'],
                 'authors': authors,
                 'authors_apa':     citations.format_authors_apa(    authors['parsed']),
                 'authors_bibtex':  citations.format_authors_bibtex( authors['parsed']),
                 'authors_chicago': citations.format_authors_chicago(authors['parsed']),
                 'authors_cse':     authors_cse,
                 'authors_mhra':    citations.format_authors_mhra(   authors['parsed']),
                 'authors_mla':     citations.format_authors_mla(    authors['parsed']),
                 'lastmod': lastmod,
                 'retrieved': datetime.now(),
                 'href': href,},
                context_instance=RequestContext(request)
            )
    return render_to_response(
        '404.html',
        {'title': page,},
        context_instance=RequestContext(request)
    )

@require_http_methods(['GET',])
def source_cite(request, encyclopedia_id, template_name='wikiprox/cite.html'):
    source = sources.source(encyclopedia_id)
    if source:
        TS_FORMAT = '%Y-%m-%dT%H:%M:%S'
        lastmod = datetime.strptime(source['modified'], TS_FORMAT)
        href = 'http://%s%s' % (request.META['HTTP_HOST'], reverse('wikiprox-source', args=[encyclopedia_id]))
        return render_to_response(
            template_name,
            {'title': encyclopedia_id,
             'lastmod': lastmod,
             'retrieved': datetime.now(),
             'href': href,},
            context_instance=RequestContext(request)
        )
    return render_to_response(
        '404.html',
        {'title': page,},
        context_instance=RequestContext(request)
    )

@require_http_methods(['GET',])
def media(request, filename, template_name='wikiprox/mediafile.html'):
    """
    """
    mediafile = None
    url = '%s/imagefile/?uri=tansu/%s' % (settings.TANSU_API, filename)
    r = requests.get(url, headers={'content-type':'application/json'})
    if r.status_code != 200:
        assert False
    response = json.loads(r.text)
    if response and (response['meta']['total_count'] == 1):
        mediafile = response['objects'][0]
    return render_to_response(
        template_name,
        {'mediafile': mediafile,
         'media_url': settings.TANSU_MEDIA_URL,},
        context_instance=RequestContext(request)
    )

@require_http_methods(['GET',])
def source(request, encyclopedia_id, template_name='wikiprox/source.html'):
    """
    """
    source = sources.source(encyclopedia_id)
    if not source:
        raise Http404
    rtmp_streamer = ''
    if source.get('streaming_url',None) and ('rtmp' in source['streaming_url']):
        source['streaming_url'] = source['streaming_url'].replace(settings.RTMP_STREAMER,'')
        rtmp_streamer = settings.RTMP_STREAMER
    return render_to_response(
        template_name,
        {'source': source,
         'SOURCES_BASE': settings.SOURCES_BASE,
         'rtmp_streamer': rtmp_streamer,},
        context_instance=RequestContext(request)
    )

def authors(request, template_name='wikiprox/authors.html'):
    authors = []
    [authors.append(page['title']) for page in encyclopedia.published_authors()]
    return render_to_response(
        template_name,
        {'authors': columnizer(authors, 4),},
        context_instance=RequestContext(request)
    )

def categories(request, template_name='wikiprox/categories.html'):
    articles_by_category = []
    categories,titles_by_category = encyclopedia.articles_by_category()
    for category in categories:
        titles = []
        [titles.append(page['title']) for page in titles_by_category[category]]
        articles_by_category.append( (category,titles) )
    return render_to_response(
        template_name,
        {'articles_by_category': articles_by_category,},
        context_instance=RequestContext(request)
    )

def contents(request, template_name='wikiprox/contents.html'):
    articles = []
    articles_a_z = encyclopedia.articles_a_z()
    for page in articles_a_z:
        articles.append( {'first_letter':page['sortkey'][0].upper(), 'title':page['title']} )
    return render_to_response(
        template_name,
        {'articles': articles,},
        context_instance=RequestContext(request)
    )

# ----------------------------------------------------------------------

def columnizer(things, cols):
    columns = []
    collen = round(len(things) / float(cols))
    col = []
    for t in things:
        col.append(t)
        if len(col) > collen:
           columns.append(col)
           col = []
    columns.append(col)
    return columns