from django.test import TestCase
from django.urls import reverse


class APIView(TestCase):

    def test_index(self):
        assert self.client.get(reverse('front-api-index')).status_code == 200

    def test_articles(self):
        data = {}
        response = self.client.get(reverse('wikiprox-api-articles'), data)
        assert response.status_code == 200
        data = {'offset': 25}
        response = self.client.get(reverse('wikiprox-api-articles'), data)
        assert response.status_code == 200

    def test_article(self):
        assert self.client.get(
            reverse('wikiprox-api-page', args=['Ansel Adams'])
        ).status_code == 200

    def test_authors(self):
        data = {}
        response = self.client.get(reverse('wikiprox-api-authors'), data)
        assert response.status_code == 200
        data = {'offset': 25}
        response = self.client.get(reverse('wikiprox-api-authors'), data)
        assert response.status_code == 200

    def test_author(self):
        assert self.client.get(
            reverse('wikiprox-api-author', args=['Brian Niiya'])
        ).status_code == 200

    #def test_sources(self):
    #    # can't browse sources independent of articles
    #    data = {}
    #    response = self.client.get(reverse('wikiprox-api-sources'), data)
    #    assert response.status_code == 200
    #    data = {'offset': 25}
    #    response = self.client.get(reverse('wikiprox-api-sources'), data)
    #    assert response.status_code == 200

    def test_source(self):
        assert self.client.get(
            reverse('wikiprox-api-source', args=['en-littletokyousa-1'])
        ).status_code == 200


class WikiPageTitles(TestCase):
    """Test that characters in MediaWiki titles are matched correctly
    """
    
    def test_wiki_titles_space(self):
        assert self.client.get(
            reverse('wikiprox-page', args=['Ansel Adams'])
        ).status_code == 200
    
    #def test_wiki_titles_period(self):
    #    assert self.client.get('/A.L.%20Wirin/').status_code == 200
    
    def test_wiki_titles_hyphen(self):
        assert self.client.get(
            reverse('wikiprox-page', args=['Aiko Herzig-Yoshinaga'])
        ).status_code == 200
    
    #def test_wiki_titles_parens(self):
    #    assert self.client.get('/Amache%20(Granada)/').status_code == 200
    
    def twiki_titleshars_comma(self):
        assert self.client.get(
            reverse('wikiprox-page', args=['December 7, 1941'])
        ).status_code == 200
    
    #def test_wiki_titles_singlequote(self):
    #    assert self.client.get("/Hawai'i/").status_code == 200
    
    def test_wiki_titles_slash(self):
        assert self.client.get(
            reverse('wikiprox-page', args=['Informants / "inu"'])
        ).status_code == 200
    
    def test_authors(self):
        response = self.client.get(reverse('wikiprox-authors'))
        assert response.status_code == 200
        content = str(response.content)
        assert 'span3 column1' in content
        assert '/authors/Brian%20Niiya/' in content
        assert 'Brian Niiya' in content
    
    def test_author(self):
        response = self.client.get(
            reverse('wikiprox-author', args=['Brian Niiya'])
        )
        assert response.status_code == 200
        content = str(response.content)
        assert 'Brian Niiya' in content
        assert 'is the content director' in content
        assert '<a href="/A.L.%20Wirin/">A.L. Wirin</a>' in content
