from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class Health(APIView):
	def get(self, request: Request):
		return Response('Server is Live!')
