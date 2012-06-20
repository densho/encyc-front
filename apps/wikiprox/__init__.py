import json
import os.path
import re

from bs4 import BeautifulSoup, SoupStrainer, Comment
import requests

from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import loader, Context


def mw_page_is_published(text):
    """Indicates whether MediaWiki page contains Category:Published template.
    """
    published = False
    soup = BeautifulSoup(text, parse_only=SoupStrainer('div', attrs={'class':'mw-content-ltr'}))
    for t in soup.find_all('table', attrs={'class':'published'}):
        published = True
    return published

def parse_mediawiki_title(text):
    """Parses the title of a MediaWiki page.
    
    Unlike most pages, "static" pages like /index, /about, and /contact
    have their nice titles in <h1> tags.  This normally results in 2 titles
    which is unsightly.
    For pages with 2 <h1> tags, remove the first one.
    """
    title = '[no title]'
    h1s = re.findall('<h1', text)
    if len(h1s) > 1:
        soup = BeautifulSoup(
            text, parse_only=SoupStrainer('div', attrs={'class':'mw-content-ltr'}))
        for t in soup.find_all('span', attrs={'class':'mw-headline'}):
            title = t.string.strip()
    else:
        soup = BeautifulSoup(text, parse_only=SoupStrainer('title'))
        title = soup.title.string.strip().replace(settings.WIKIPROX_MEDIAWIKI_TITLE, '')
    return title

def parse_mediawiki_text(text):
    """Parses the body of a MediaWiki page.
    """
    soup = BeautifulSoup(
        text, parse_only=SoupStrainer('div', attrs={'class':'mw-content-ltr'}))
    soup = remove_staticpage_titles(soup)
    soup = remove_comments(soup)
    soup = remove_edit_links(soup)
    soup = rewrite_mediawiki_urls(soup)
    soup = rewrite_newpage_links(soup)
    soup = rewrite_prevnext_links(soup)
    sources = find_primary_sources(soup)
    soup = format_primary_sources(soup, sources)
    return unicode(soup)


def remove_staticpage_titles(soup):
    """strip extra <h1> on "static" pages

    "Static" pages will have an extra <h1> in the page body.
    This is extracted by parse_mediawiki_title so now we need
    to remove it.
    """
    h1s = soup.find_all('h1')
    if h1s:
        for h1 in soup.find_all('h1'):
            h1.decompose()
    return soup

def remove_comments(soup):
    """TODO Removes MediaWiki comments from page text
    """
    #def iscomment(tag):
    #    return isinstance(text, Comment)
    #comments = soup.findAll(iscomment)
	#[comment.extract() for comment in comments]
    return soup

def remove_edit_links(soup):
    """Removes [edit] spans (ex: <span class="editsection">)
    
    Security precaution: we don't want people to be able to edit, or to find edit links.
    """
    for e in soup.find_all('span', attrs={'class':'editsection'}):
        e.decompose()
    return soup

def rewrite_mediawiki_urls(soup):
    """Rewrites /mediawiki/index.php/... URLs to /...
    """
    for a in soup.find_all('a', href=re.compile('/mediawiki/index.php')):
        a['href'] = a['href'].replace('/mediawiki/index.php', '')
    return soup

def rewrite_newpage_links(soup):
    """Rewrites new-page links
    
    ex: http://.../mediawiki/index.php?title=Nisei&amp;action=edit&amp;redlink=1
    """
    for a in soup.find_all('a', href=re.compile('action=edit')):
        a['href'] = a['href'].replace('?title=', '/')
        a['href'] = a['href'].replace('&action=edit', '')
        a['href'] = a['href'].replace('&redlink=1', '')
    return soup

def rewrite_prevnext_links(soup):
    """Rewrites previous/next links
    
    ex: http://.../mediawiki/index.php?title=Category:Pages_Needing_Primary_Sources&pagefrom=Mary+Oyama+Mittwer
    """
    for a in soup.find_all('a', href=re.compile('pagefrom=')):
        a['href'] = a['href'].replace('?title=', '/')
        a['href'] = a['href'].replace('&pagefrom=', '?pagefrom=')
    for a in soup.find_all('a', href=re.compile('pageuntil=')):
        a['href'] = a['href'].replace('?title=', '/')
        a['href'] = a['href'].replace('&pageuntil=', '?pageuntil=')
    return soup

def extract_encyclopedia_id(uri):
    """Attempts to extract a valid Densho encyclopedia ID from the URI
    
    TODO Check if valid encyclopedia ID
    """
    if 'thumb' in uri:
        path,filename = os.path.split(os.path.dirname(uri))
        eid,ext = os.path.splitext(filename)
    else:
        path,filename = os.path.split(uri)
        eid,ext = os.path.splitext(filename)
    return eid
    
def find_primary_sources(soup):
    """Scan through the soup for <a><img>s and get the ones with encyclopedia IDs.
    """
    sources = []
    imgs = []
    eids = []
    # all the <a><img>s
    for a in soup.find_all('a', attrs={'class':'image'}):
        imgs.append(a.img)
    # anything that might be an encyclopedia_id
    for img in imgs:
        encyclopedia_id = extract_encyclopedia_id(img['src'])
        if encyclopedia_id:
            eids.append(encyclopedia_id)
    # get sources via sources API
    sources = {}
    if eids:
        eid_args = []
        for eid in eids:
            eid_args.append('encyclopedia_id__in=%s' % eid)
        url = '%s/primarysource/?%s' % (settings.TANSU_API, '&'.join(eid_args))
        r = requests.get(url, headers={'content-type':'application/json'})
        if r.status_code == 200:
            response = json.loads(r.text)
            for s in response['objects']:
                sources[s['encyclopedia_id']] = s
    return sources

def format_primary_sources(soup, sources):
    """Rewrite image HTML so primary sources appear in pop-up lightbox with metadata.
    
    see http://192.168.0.13/redmine/attachments/4/Encyclopedia-PrimarySourceDraftFlow.pdf
    """
    # all the <a><img>s
    contexts = []
    num_sources = 0
    for a in soup.find_all('a', attrs={'class':'image'}):
        num_sources = num_sources + 1
    for a in soup.find_all('a', attrs={'class':'image'}):
        encyclopedia_id = extract_encyclopedia_id(a.img['src'])
        href = None
        if encyclopedia_id and (encyclopedia_id in sources.keys()):
            source = sources[encyclopedia_id]
            template = 'wikiprox/generic.html'
            # rewrite more-info URL
            x,y = a['href'].split('File:')
            eid,ext = os.path.splitext(y)
            href = reverse('wikiprox-source', kwargs={'encyclopedia_id': eid })
        if href:
            # context
            common = {'media_format': source['media_format'],
                      'MEDIA_URL': settings.MEDIA_URL,
                      'SOURCE_MEDIA_URL': settings.TANSU_MEDIA_URL,
                      'href': href,
                      'caption': source['caption'],
                      'courtesy': source['courtesy'],
                      'multiple': num_sources > 1,}
            specific = {}
            # video
            if source['media_format'] == 'video':
                template = 'wikiprox/video.html'
                if source.get('thumbnail_sm',None):
                    thumb_sm = source['thumbnail_sm']
                    thumb_lg = source['thumbnail_lg']
                elif source.get('display',None):
                    thumb_sm = source['display']
                    thumb_lg = source['display']
                else:
                    thumb_sm = 'img/icon-video.png'
                    thumb_lg = 'img/icon-video.png'
                xy = [640,480]
                if source.get('aspect_ratio',None) and (source['aspect_ratio'] == 'hd'):
                    xy = [640,360]
                # remove rtmp_streamer from streaming_url
                if source.get('streaming_url',None) and ('rtmp' in source['streaming_url']):
                    streaming_url = source['streaming_url'].replace(settings.RTMP_STREAMER, '')
                    rtmp_streamer = settings.RTMP_STREAMER
                else:
                    streaming_url = source['streaming_url']
                    rtmp_streamer = ''
                # add 20px to vertical for JWplayer
                xy[1] = xy[1] + 20
                specific = {
                    'thumb_sm': thumb_sm,
                    'thumb_lg': thumb_lg,
                    'rtmp_streamer': rtmp_streamer,
                    'streaming_url': streaming_url,
                    'xy': xy,
                    }
            # document
            elif source['media_format'] == 'document':
                template = 'wikiprox/document.html'
                if source.get('thumbnail_sm',None):
                    thumb_sm = source['thumbnail_sm']
                    thumb_lg = source['thumbnail_lg']
                elif source.get('display',None):
                    thumb_sm = source['thumbnail_sm']
                    thumb_lg = source['thumbnail_lg']
                elif source.get('original',None):
                    thumb_sm = source['original']
                    thumb_lg = source['original']
                else:
                    thumb_sm = 'img/icon-document.png'
                    thumb_lg = 'img/icon-document.png'
                specific = {
                    'thumb_sm': thumb_sm,
                    'thumb_lg': thumb_lg,
                    }
            # image
            elif source['media_format'] == 'image':
                template = 'wikiprox/image.html'
                # img src
                if source.get('thumbnail_sm',None):
                    thumb_sm = source['thumbnail_sm']
                    thumb_lg = source['thumbnail_lg']
                elif source.get('display',None):
                    thumb_sm = source['display']
                    thumb_lg = source['display']
                elif source.get('original',None):
                    thumb_sm = source['original']
                    thumb_lg = source['original']
                else:
                    thumb_sm = 'img/icon-image.png'
                    thumb_lg = 'img/icon-image.png'
                specific = {
                    'thumb_sm': thumb_sm,
                    'thumb_lg': thumb_lg,
                    }
            context = dict(common.items() + specific.items())
            contexts.append(context)
            # render
            t = loader.get_template(template)
            c = Context(context)
            img = BeautifulSoup(t.render(c))
            # insert back into page
            a.replace_with(img.body)
    return soup
