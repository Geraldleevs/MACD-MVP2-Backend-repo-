FROM python:3.13.2-slim AS base

# Use .venv to let it copy to another stage
ENV PATH="/.venv/bin:$PATH"
ENV LD_LIBRARY_PATH="/.venv/lib"
ENV TA_LIBRARY_PATH="/.venv/lib"
ENV TA_INCLUDE_PATH="/.venv/include"


# --- INSTALL TA-LIB REQUIREMENTS ---
FROM base AS ta_lib
RUN apt-get update && \
	apt-get install -y --no-install-recommends build-essential gcc wget && \
	apt clean && \
	python -m venv /.venv
RUN wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
	tar -xvzf ta-lib-0.6.4-src.tar.gz && \
	cd ta-lib-0.6.4 && \
	./configure --prefix=/.venv && \
	make && \
	make install && \
	cd .. && \
	rm -rf ../ta-lib*
RUN pip install ta-lib==0.6.4


# --- INSTALL SERVER PACKAGES
FROM base AS server_packages
COPY --from=ta_lib /.venv /.venv
COPY requirements-server.txt /requirements-server.txt
RUN pip install -r /requirements-server.txt --no-cache-dir


# --- INSTALL PIP PACKAGES
FROM base AS packages
COPY --from=server_packages /.venv /.venv
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt --no-cache-dir


# --- BUILD APPLICATION ---
FROM base AS server
ARG PORT=8080
EXPOSE ${PORT}

# Add TA library to ld config
COPY --from=packages /.venv /.venv
RUN echo "include /.venv/lib" >> /etc/ld.so.conf && \
	ldconfig && \
	mkdir /app
WORKDIR /app
COPY . .

ENV EXCLUDE_FIRESTORE="True"
RUN python manage.py migrate
ENV EXCLUDE_FIRESTORE="False"

CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 8 --timeout 0 --preload machd.wsgi:application
