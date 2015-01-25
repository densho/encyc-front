"""
example walkthrough:
------------------------------------------------------------------------

HOSTS = [{'host':'192.168.56.101', 'port':9200}]
INDEX = 'encyc-dev'

from wikiprox import docstore
from wikiprox import models

docstore.delete_index(HOSTS, INDEX)

docstore.create_index(HOSTS, INDEX)

doc_type = 'authors'
authors = models.Wiki.authors(columnize=False)
for title in authors:
    print(title)
    page = models.Page(title)
    docstore.post(HOSTS, INDEX, doc_type, title, page.__dict__)

doc_type = 'articles'
contents = models.Wiki.contents()
titles = []
import random
while len(titles) < 10:
    page = random.choice(contents)
    if not page['title'] in titles:
        titles.append(page['title'])

for title in titles:
    page = models.Page(title)
    docstore.post(HOSTS, INDEX, doc_type, title, page.__dict__)

------------------------------------------------------------------------
"""

from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os

from elasticsearch import Elasticsearch


MAX_SIZE = 1000000
DEFAULT_PAGE_SIZE = 20


def _get_connection(hosts):
    es = Elasticsearch(hosts)
    return es

def index_exists(hosts, index):
    """
    @param hosts: list of dicts containing host information.
    @param index:
    @param model:
    @param document_id:
    """
    es = _get_connection(hosts)
    return es.indices.exists(index=index)

def create_index(hosts, index):
    """Creates the specified index if it does not already exist.
    
    @param hosts: list of dicts containing host information.
    @param index: Name of the target index.
    @returns: JSON dict with status codes and responses
    """
    logger.debug('_create_index(%s, %s)' % (hosts, index))
    body = {
        'settings': {},
        'mappings': {}
        }
    es = _get_connection(hosts)
    status = es.indices.create(index=index, body=body)
    return status

def delete_index(hosts, index):
    """Delete the specified index.
    
    @param hosts: list of dicts containing host information.
    @param index: Name of the target index.
    @returns: JSON dict with status code and response
    """
    logger.debug('_delete_index(%s, %s)' % (hosts, index))
    es = _get_connection(hosts)
    if index_exists( hosts, index ):
        status = es.indices.delete(index=index)
        return status
    return '{"status":500, "message":"Index does not exist"}'

def post(hosts, index, doc_type, url_title, document):
    """Add a new document to an index or update an existing one.
    
    curl -XPUT 'http://localhost:9200/encyc-dev/article/Tule%20Lake' -d '{ ... }'
    
    @param hosts: list of dicts containing host information.
    @param index: 
    @param doc_type: 
    @param url_title: 
    @param document: The object to post.
    @returns: JSON dict with status code and response
    """
    logger.debug('post(%s, %s, %s)' % (hosts, index, url_title))
    es = _get_connection(hosts)
    status = es.index(index=index, doc_type=doc_type, id=url_title, body=document)
    return status


def exists(hosts, index, model, document_id):
    """
    @param hosts: list of dicts containing host information.
    @param index:
    @param model:
    @param document_id:
    """
    es = _get_connection(hosts)
    return es.exists(index=index, doc_type=model, id=document_id)


def get(hosts, index, model, document_id, fields=None):
    """
    @param hosts: list of dicts containing host information.
    @param index:
    @param model:
    @param document_id:
    @param fields:
    """
    es = _get_connection(hosts)
    if exists(hosts, index, model, document_id):
        if fields is not None:
            return es.get(index=index, doc_type=model, id=document_id, fields=fields)
        return es.get(index=index, doc_type=model, id=document_id)
    return None

def _clean_dict(data):
    """Remove null or empty fields; ElasticSearch chokes on them.
    
    >>> d = {'a': 'abc', 'b': 'bcd', 'x':'' }
    >>> _clean_dict(d)
    >>> d
    {'a': 'abc', 'b': 'bcd'}
    
    @param data: Standard DDR list-of-dicts data structure.
    """
    if data and isinstance(data, dict):
        for key in data.keys():
            if not data[key]:
                del(data[key])

def _clean_sort(sort):
    """Take list of [a,b] lists, return comma-separated list of a:b pairs
    
    >>> _clean_sort( 'whatever' )
    >>> _clean_sort( [['a', 'asc'], ['b', 'asc'], 'whatever'] )
    >>> _clean_sort( [['a', 'asc'], ['b', 'asc']] )
    'a:asc,b:asc'
    """
    cleaned = ''
    if sort and isinstance(sort,list):
        all_lists = [1 if isinstance(x, list) else 0 for x in sort]
        if not 0 in all_lists:
            cleaned = ','.join([':'.join(x) for x in sort])
    return cleaned

def search(hosts, index, model='', query='', term={}, filters={}, sort=[], fields=[], first=0, size=MAX_SIZE):
    """Run a query, get a list of zero or more hits.
    
    @param hosts: list of dicts containing host information.
    @param index: Name of the target index.
    @param model: Type of object ('articles', 'authors')
    @param query: User's search text
    @param term: dict
    @param filters: dict
    @param sort: list of (fieldname,direction) tuples
    @param fields: str
    @param first: int Index of document from which to start results
    @param size: int Number of results to return
    @returns raw ElasticSearch query output
    """
    logger.debug('search( hosts=%s, index=%s, model=%s, query=%s, term=%s, filters=%s, sort=%s, fields=%s, first=%s, size=%s' % (hosts, index, model, query, term, filters, sort, fields, first, size))
    _clean_dict(filters)
    _clean_dict(sort)
    body = {}
    if term:
        body['query'] = {}
        body['query']['term'] = term
    if filters:
        body['filter'] = {'term':filters}
    logger.debug(json.dumps(body))
    sort_cleaned = _clean_sort(sort)
    fields = ','.join(fields)
    es = _get_connection(hosts)
    if query:
        results = es.search(
            index=index,
            doc_type=model,
            q=query,
            body=body,
            sort=sort_cleaned,
            size=size,
            fields=fields,
        )
    else:
        results = es.search(
            index=index,
            doc_type=model,
            body=body,
            sort=sort_cleaned,
            size=size,
            fields=fields,
        )
    return results

class Page(object):
    pass

def articles(hosts, index):
    results = search(
        hosts, index, model='articles',
        term={}, filters={}, sort=[],
        fields=['title', 'published'],
        first=0, size=MAX_SIZE)
    data = []
    for hit in results['hits']['hits']:
        data.append(hit['fields']['title'][0])
    return data

def contents(hosts, index):
    titles = articles(hosts, index)
    data = [
        {'title': title, 'first_letter': title[0]}
        for title in titles
    ]
    return data

def article(hosts, index, title):
    results = get(hosts, index, 'articles', title)
    page = Page()
    for key,val in results['_source'].iteritems():
        setattr(page, key, val)
    return page

def authors(hosts, index):
    results = search(
        hosts, index, model='authors',
        term={}, filters={}, sort=[],
        fields=['title', 'public'],
        first=0, size=MAX_SIZE)
    data = []
    for hit in results['hits']['hits']:
        data.append(hit['fields']['title'][0])
    return data

def author(hosts, index, title):
    results = get(hosts, index, 'authors', title)
    return results['_source']