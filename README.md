# scrape-cpi
Scrape ODU's CPI site for projects.
Based on [scrapy](https://scrapy.org/).



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



# Run crawler HTTP API server

```bash
source .virt/bin/activate
python rest_server.py
```


> Windows can be a pain to setup Python. Use Cygwin or install a Linux virtual machine.
