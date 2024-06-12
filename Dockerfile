FROM python:3.7-slim
RUN mkdir -p /app
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir
ADD . ./
EXPOSE 8000
CMD python manage.py migrate && python manage.py runserver 0.0.0.0:8000
