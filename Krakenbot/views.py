from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from Krakenbot.recommendation import Recommendation

class RecommendationView(APIView):
	def get(self, request: Request):
			token_id = request.query_params.get('token_id', '').upper()
			timeframe = request.query_params.get('timeframe', '').lower()
			result = Recommendation(token_id, timeframe).recommend()
			return Response(result, 200)
