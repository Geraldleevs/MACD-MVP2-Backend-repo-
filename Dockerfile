FROM python:3.12.4-slim AS base

# Use venv to let it copy to another stage
ENV PATH="/venv/bin:$PATH"
ENV LD_LIBRARY_PATH="/venv/lib"
ENV TA_LIBRARY_PATH="/venv/lib"
ENV TA_INCLUDE_PATH="/venv/include"


# --- INSTALL PIP REQUIREMENTS ---
FROM base AS compile
COPY requirements-docker.txt ./requirements.txt
RUN python -m venv /venv && \
	pip install -r requirements.txt --no-cache-dir


# --- INSTALL TA-LIB
FROM base AS ta_lib
COPY --from=compile /venv /venv
RUN apt-get update && \
	apt-get install -y --no-install-recommends build-essential gcc wget && \
	apt clean && \
	wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
	tar -xvzf ta-lib-0.4.0-src.tar.gz && \
	cd ta-lib && \
	./configure --prefix=/venv && \
	make && \
	make install && \
	pip install ta-lib==0.5.1 && \
	rm -rf ../ta-lib*


# --- INSTALL SERVER REQUIREMENTS ---
FROM base AS server
COPY --from=ta_lib /venv /venv
COPY requirements-server.txt ./requirements.txt
RUN pip install -r requirements.txt


# --- BUILD APPLICATION ---
FROM base AS build
ARG PORT=8080
EXPOSE ${PORT}

# Add TA library to ld config
RUN echo "include /venv/lib" >> /etc/ld.so.conf && \
	ldconfig && \
	mkdir /app
WORKDIR /app
COPY --from=server /venv /venv
COPY . .

ENV IMAGE_BUILDING="BUILDING"
RUN python manage.py migrate
ENV IMAGE_BUILDING="FINISHED"

CMD gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 0 --preload Krakenbot.asgi:application -k Krakenbot.uvicorn_workers.UvicornWorker
