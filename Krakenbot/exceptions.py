class NotEnoughTokenException(Exception):
	pass

class NotAuthorisedException(Exception):
	pass

class BadRequestException(Exception):
	pass

class SessionExpiredException(Exception):
	pass

class DatabaseIncorrectDataException(Exception):
	pass

class ServerErrorException(Exception):
	pass


class NoUserSelectedException(Exception):
	pass
