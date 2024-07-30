FROM python:3.12.4-slim AS base
ENV PATH="/venv/bin:$PATH"
ENV LD_LIBRARY_PATH="/venv/lib"
ENV TA_LIBRARY_PATH="/venv/lib"
ENV TA_INCLUDE_PATH="/venv/include"

FROM base AS compile
# Use venv to let it copy to another stage
RUN python -m venv /venv

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc wget
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
	tar -xvzf ta-lib-0.4.0-src.tar.gz && \
	cd ta-lib/ && \
	./configure --prefix=/venv && \
	make && \
	make install

COPY docker-requirements.txt ./requirements.txt
RUN pip install -r requirements.txt --no-cache-dir
RUN pip install ta-lib
RUN rm -R ta-lib ta-lib-0.4.0-src.tar.gz

FROM base AS build
COPY --from=compile /venv /venv
RUN echo "include /venv/lib" >> /etc/ld.so.conf
RUN ldconfig

ARG PORT=8080
RUN mkdir -p /app
WORKDIR /app
ADD . .
EXPOSE ${PORT}
CMD python manage.py migrate && python manage.py runserver
