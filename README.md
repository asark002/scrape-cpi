# scrape-cpi
Scrape ODU's CPI site for projects.
Based on [scrapy](https://scrapy.org/).


# Requirements

* Python 2.7+ or 3.4+


# Installation

```bash
git clone https://github.com/asark002/scrape-cpi.git
cd scrape-cpi
```

### Create a virtual environment (`virtualenv` or `venv`)

```bash
python3 -m venv .virt
source .virt/bin/activate
pip install scrapy scrapyrt
```

### Run scraper

```bash
source .virt/bin/activate
scrapy crawl projects
```

> Windows can be a pain to setup Python. Use Cygwin or install a Linux virtual machine.
