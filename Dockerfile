FROM python:3.12.4-slim
ARG PORT=8080
RUN mkdir -p /app
WORKDIR /app
COPY docker-requirements.txt ./requirements.txt
RUN pip install -r requirements.txt --no-cache-dir
ADD . .
EXPOSE ${PORT}
CMD python manage.py migrate && python manage.py runserver
