from datetime import timedelta
from typing import List
from rest_framework.request import Request
from Krakenbot.models.firebase_news import FirebaseNews, NewsField
from django.utils import timezone
import os
import requests

from Krakenbot.utils import authenticate_scheduler_oicd

class News:
	GNEWS_ENDPOINT = "https://gnews.io/api/v4/search"
	DEFAULT_MAX_FETCH = 10
	DEFAULT_EXPIRY_DAY = 14

	def __init__(self):
		self.API_KEY = os.environ.get('GNEWS_API_KEY')
		self.QUERIES = os.environ.get('GNEWS_FETCH_KEYWORD', 'bitcoin:BTC').split(',')
		self.LANG = 'en'
		try:
			self.MAX_FETCH = float(os.environ.get('GNEWS_MAX_FETCH'))
			self.EXPIRY_DAY = float(os.environ.get('NEWS_EXPIRED_IN_DAY'))
		except ValueError:
			self.MAX_FETCH = self.DEFAULT_MAX_FETCH
			self.EXPIRY_DAY = self.DEFAULT_EXPIRY_DAY

	def parse_gnews(self, gnews_result):
		articles = gnews_result.get('articles', [])
		results: List[NewsField] = [{
			'time': timezone.datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
			'title': article['title'],
			'description': article['description'],
			'content': article['content'],
			'banner_image': article['image'],
			'url': article['url'],
			'source': article['source']['name']
			} for article in articles]
		return results

	def fetch_news(self, request: Request):
		authenticate_scheduler_oicd(request)
		firebase_news = FirebaseNews()

		delete_before_time = timezone.now() - timedelta(days=self.EXPIRY_DAY)
		firebase_news.delete_all_before(delete_before_time)

		fetch_from_time = timezone.now() - timedelta(days=5)
		fetch_from_time = fetch_from_time.strftime('%Y-%m-%dT%H:%M:%SZ')

		cur_query_index = firebase_news.fetch_next_query().get('id', 0) % len(self.QUERIES)
		[cur_query, cur_tag] = self.QUERIES[cur_query_index].split(':')

		results = requests.get(self.GNEWS_ENDPOINT, params={
			'apikey': self.API_KEY,
			'q': cur_query,
			'lang': self.LANG,
			'from': fetch_from_time,
			'max': self.MAX_FETCH
		}).json()
		results = self.parse_gnews(results)

		for result in results:
			firebase_news.upsert(result, cur_tag)

		firebase_news.update_next_query(cur_query_index + 1)
