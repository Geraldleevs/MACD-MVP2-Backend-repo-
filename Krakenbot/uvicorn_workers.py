from uvicorn.workers import UvicornWorker as BaseUvicornWorker


class UvicornWorker(BaseUvicornWorker):
	CONFIG_KWARGS = { "loop": "uvloop", "lifespan": "off" }
