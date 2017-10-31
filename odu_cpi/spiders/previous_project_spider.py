import scrapy

from odu_cpi import items


class PreviousProjectSpider(scrapy.Spider):

    name = 'projects'
    start_urls = ['http://www.cs.odu.edu/~cpi/previous410-411.html']

    def parse(self, response):
        """
        """
        if response.status == 200:
            columns = response.xpath('//div[@class="container"]//div//div[@class="col-2"]')
            for col in columns:
                course = col.xpath('.//h2/text()').extract_first()
                if course == 'CS 410 Previous Projects- Web Pages':
                    course = 'CS 410'
                elif course == 'CS 411 Previous Projects- Web Pages':
                    course = 'CS 411'

                for item in col.xpath('.//ul//li//a'):
                    name = item.xpath('.//text()').extract_first().replace('\n', '')
                    link = item.xpath('.//@href').extract_first()
                    follow = response.follow(
                        link,
                        callback = self.parse_projects,
                        errback = self.request_error,
                        meta = {
                            'course': course,
                            'project_name': name,
                            'splash': {
                                'args': {
                                    'html': 1,
                                    'png': 1,
                                }
                            }
                        }
                    )
                    #print('{0} - {1}: {2}'.format(cs_course, name, follow.url))
                    yield follow

    def parse_projects(self, response):
        """
        """
        content = response.xpath('//body')
        if len(content) == 1:
            cpi_item = items.OduCpiItem(
                course = response.meta['course'],
                project_name = response.meta['project_name'],
                url = response.url,
                content = content[0].root)
            yield cpi_item

    def request_error(self, failure):
        """
        """

