FROM python:3.6-alpine
ADD . /opt/crawler
WORKDIR /opt/crawler
RUN apk update
RUN apk add gcc musl-dev libffi-dev libxml2-dev libxslt-dev openssl-dev
RUN pip install -r requirements.txt
RUN export SCRAPY_SETTINGS_MODULE=odu_cpi.settings
CMD ["python", "rest_server.py"]
