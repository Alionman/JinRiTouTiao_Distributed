# -*- coding: utf-8 -*-
import logging
import scrapy
from scrapy_splash import SplashRequest
from scrapy.linkextractors import LinkExtractor
from ..items import ToutiaoItem
from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str

#将最终的各个请求信息输出到日志中
logger = logging.getLogger(__name__)
logger.setLevel(level = logging.INFO)
handler = logging.FileHandler("log.txt")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

#lua脚本，头条下拉滚动加载，用js获取当前头条最后一列并且聚集，仿造动态下滚事件
subject_script = '''
    function main(splash)
    local scroll_times = 1
    splash:go(splash.args.url)
    splash:wait(1)
    for i=1,scroll_times do
        splash:runjs("document.querySelectorAll('div.wcommonFeed li.item')[document.querySelectorAll('div.wcommonFeed li.item').length-1].scrollIntoView(true)")
        splash:wait(1)
    end
    return splash:html()
end
'''

class HeadlinesSpider(RedisSpider):
    name = 'headline'
    allowed_domains = ['www.toutiao.com']
    base_url = 'http://www.toutiao.com/'

#    def start_requests(self):
#        yield SplashRequest(self.base_url, callback=self.parse_subject_urls, dont_filter=True)

    def make_request_from_data(self, data):
        url = bytes_to_str(data, self.redis_encoding)
        return self.make_requests_from_url(url)

    def make_requests_from_url(self, url):
        return SplashRequest(url, dont_filter=True)

    def parse(self, response):
        le = LinkExtractor(restrict_css='div.channel ul')
        links = le.extract_links(response)
        #去除图片项，热点项节推荐项（内容与各分模块重复）
        del links[2]
        del links[1]
        del links[0]
        links=links[:8]
        for link in links:
            #获取各个分模块的页面链接，运用lua脚本动态渲染加载链接
            logger.info("current subject link is:%s" % link.url)
            yield SplashRequest(link.url, callback=self.parse_title_urls, endpoint='execute', args={'lua_source':subject_script}, cache_args=['lua_source'])

    def parse_title_urls(self, response):
        hrefs = response.css('div.wcommonFeed ul li div.title-box a::attr(href)').re('/group/(.*)')
        for href in hrefs:
            url = '%sa%s' % (self.base_url,href)
            #向各个热点发起下载请求
            logger.info("current title url is:%s" % url)
            yield SplashRequest(url, callback=self.parse_subject_urls)

    def parse_subject_urls(self, response):
        headline = ToutiaoItem()
        headline['subject'] = response.css('div.middlebar div.bui-left.chinese-tag a:nth-child(2)::text').extract_first()
        headline['title'] = response.css('h1::text').extract_first()
        content = response.css('div.bui-left.index-middle p::text').extract()
        headline['content'] = ' '.join(content)
        yield headline

