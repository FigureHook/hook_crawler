import os

# Scrapy settings for gsc_crawler project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'product_crawler'

SPIDER_MODULES = ['product_crawler.spiders']
NEWSPIDER_MODULE = 'product_crawler.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
# SER_AGENT = 'gsc_crawler (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# ONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html# ownload-delay
# See also autothrottle settings and docs
# OWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# ONCURRENT_REQUESTS_PER_DOMAIN = 16
# ONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# OOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# ELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'gsc_crawler.middlewares.GscCrawlerSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    'gsc_crawler.middlewares.GscCrawlerDownloaderMiddleware': 543,
# }

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'product_crawler.pipelines.SaveProductInDatabasePipeline': 400,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# UTOTHROTTLE_ENABLED = True
# The initial download delay
# UTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# UTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# UTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# UTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html# ttpcache-middleware-settings
# TTPCACHE_ENABLED = True
# TTPCACHE_EXPIRATION_SECS = 0
# TTPCACHE_DIR = 'httpcache'
# TTPCACHE_IGNORE_HTTP_CODES = []
# TTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# scrapy-proxies settings

RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 503, 504, 400, 403, 404, 408]

DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
    'scrapy_proxies.RandomProxy': 100,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
}

PROXY_LIST = os.getenv(
    'PROXY_LIST',
    '/workspace/Services/crawler/proxy-list.txt'
)
PROXY_MODE = 0


# logger settings
LOG_LEVEL = 'INFO'
