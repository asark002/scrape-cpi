# scrape-cpi
Scrape ODU's CPI site for projects.
Based on [scrapy](https://scrapy.org/).


> Windows can be a pain to setup Python. Use Cygwin or install a Linux virtual machine.



# Prerequisites

* Python 2.7+ or 3.4+
* [Docker](https://store.docker.com/search?type=edition&offering=community)
* (optional) [Docker Compose](https://docs.docker.com/compose/install/)



# Install from source

Checkout the repo

```bash
git clone https://github.com/asark002/scrape-cpi.git
cd scrape-cpi
```

Create a virtual environment (`virtualenv` or `venv`) and install the packages for the crawler.

```bash
python3 -m venv .virt
source .virt/bin/activate
pip install -r requirements.txt
```



# Start Splash service (Docker)

The [`splash`](https://splash.readthedocs.io/en/stable/) service is the Javascript render engine that behaves like a web browser.
Mariana's crawler component uses this service so that the HTML content can be fully rendered prior to scraping.
Docker is the easiest way to run this service:

```bash
docker pull scrapinghub/splash
docker run -p 8050:8050 scrapinghub/splash
```



# Run crawler HTTP API server

```bash
source .virt/bin/activate
python rest_server.py
```



# Run using Docker Compose

```bash
version: '3'
services:
  crawler-http-api:
    build:
      context: .
      dockerfile: ./Dockerfile
      
    ports:
      - "9801:9801"
    links:
      - splash
      - elasticsearch

  splash:
    image: "scrapinghub/splash"
    ports:
      - 8050:8050

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch-oss:6.2.2
    container_name: elasticsearch
    environment:
      - cluster.name=docker-cluster
      - bootstrap.memory_lock=true
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - esdata1:/usr/share/elasticsearch/data
    ports:
      - 9200:9200

volumes:
  esdata1:
    driver: local
```
