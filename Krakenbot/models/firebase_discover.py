try:
	from Krakenbot import settings
except ModuleNotFoundError:
	from local_settings import settings

class FirebaseDiscover:
	def __init__(self):
		self.__discover = settings.firebase.collection(u'discover')

	def save(self, token_id: str, about: str):
		doc_ref = self.__discover.document(token_id)
		if doc_ref.get().exists:
			doc_ref.update({ 'about': about })
		else:
			doc_ref.set({ 'about': about, 'token_id': token_id })
