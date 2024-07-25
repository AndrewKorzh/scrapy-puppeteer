import json
import logging
from collections import defaultdict
from typing import List, Union
from urllib.parse import urlencode, urljoin

from scrapy import signals
from scrapy.crawler import Crawler
from scrapy.exceptions import IgnoreRequest, NotConfigured, DontCloseSpider
from scrapy.http import Headers, TextResponse, Response
from scrapy.utils.log import failure_to_exc_info
from twisted.python.failure import Failure
import time

from scrapypuppeteer.actions import (
    Click,
    GoBack,
    GoForward,
    GoTo,
    RecaptchaSolver,
    Screenshot,
    Scroll,
    CustomJsAction,
)
from scrapypuppeteer.response import (
    PuppeteerResponse,
    PuppeteerHtmlResponse,
    PuppeteerScreenshotResponse,
    PuppeteerRecaptchaSolverResponse,
    PuppeteerJsonResponse,
)
from scrapypuppeteer.request import ActionRequest, PuppeteerRequest, CloseContextRequest



import asyncio
from pyppeteer import launch
import syncer
import uuid
import base64

class ContextManager:

    def __init__(self):
        #self.browser = "browser"
        self.browser = syncer.sync(launch())
        #тут инициализация брацщера
        self.contexts = {}
        self.pages = {}
        self.context_page_map = {}


    async def check_context_and_page(self, context_id, page_id):
        if not context_id or not page_id:
            context_id, page_id = await self.open_new_page()
        return context_id, page_id

    async def open_new_page(self):
        print("New Page Was Created")
        context_id = uuid.uuid4().hex.upper()
        page_id = uuid.uuid4().hex.upper()

        # --- Создание страницы и добавление её в структуру --- #
        self.contexts[context_id] = await self.browser.createIncognitoBrowserContext()
        self.pages[page_id] = await self.contexts[context_id].newPage()
        self.context_page_map[context_id] = page_id
        #-------------------------------------------------------#

        return context_id, page_id

    def get_page_by_id(self, context_id, page_id):
        return self.pages[page_id]

    def print_context_page_map(self):
        print("\nContexts")
        print(self.context_page_map)
        print()

    def close_browser(self):
        if self.browser:
            syncer.sync(self.browser.close())

    def __del__(self):
        self.close_browser()



class LocalScrapyPyppeteer:
#class BrowserManager:
    def __init__(self):
        self.context_manager = ContextManager()

    def process_puppeteer_request(self, action_request: ActionRequest):
        endpoint = action_request.action.endpoint
        if endpoint == "goto":
            puppeteer_html_response = self.goto(action_request)
            return puppeteer_html_response
        elif endpoint == "click":
            puppeteer_html_response = self.click(action_request)
            return puppeteer_html_response
        elif endpoint == "back":
            puppeteer_html_response = self.go_back(action_request)
            return puppeteer_html_response
        elif endpoint == "forward":
            puppeteer_html_response = self.go_forward(action_request)
            return puppeteer_html_response
        elif endpoint == "screenshot":
            puppeteer_screenshot_response = self.screenshot(action_request)
            return puppeteer_screenshot_response


        return None

    def goto(self, action_request: ActionRequest):
        puppeteer_request = action_request.meta.get("puppeteer_request")
        context_id, page_id = syncer.sync(self.context_manager.check_context_and_page(puppeteer_request.context_id, puppeteer_request.page_id))
        page = self.context_manager.get_page_by_id(context_id, page_id)

        async def async_goto():
            url = action_request.action.payload()["url"]
            service_url = action_request.url
            cookies = action_request.cookies

            await page.goto(url)

            #Wait options
            wait_options = action_request.action.payload().get("waitOptions", {}) or {}
            timeout = wait_options.get("selectorOrTimeout", 1000)
            visible = wait_options.get("visible", False)
            hidden = wait_options.get("hidden", False)

            if isinstance(timeout, (int, float)):
                await asyncio.sleep(timeout / 1000)
            else:
                await page.waitFor(selector=timeout, options={
                    'visible': visible,
                    'hidden': hidden,
                    'timeout': 30000
                })
            #Wait options

            response_html = await page.content()

            puppeteer_html_response = PuppeteerHtmlResponse(service_url,
                                        puppeteer_request,
                                        context_id = context_id,
                                        page_id = page_id,
                                        html = response_html,
                                        cookies=cookies)

            return puppeteer_html_response
        return syncer.sync(async_goto())

    def click(self, action_request: ActionRequest):
        puppeteer_request = action_request.meta.get("puppeteer_request")
        context_id, page_id = syncer.sync(self.context_manager.check_context_and_page(puppeteer_request.context_id, puppeteer_request.page_id))
        page = self.context_manager.get_page_by_id(context_id, page_id)

        async def async_click():
            selector = action_request.action.payload().get("selector")
            cookies = action_request.cookies
            click_options = action_request.action.click_options
            await page.click(selector, click_options)
            #Wait options
            wait_options = action_request.action.payload().get("waitOptions", {}) or {}
            timeout = wait_options.get("selectorOrTimeout", 1000)
            visible = wait_options.get("visible", False)
            hidden = wait_options.get("hidden", False)

            if isinstance(timeout, (int, float)):
                await asyncio.sleep(timeout / 1000)
            else:
                await page.waitFor(selector=timeout, options={
                    'visible': visible,
                    'hidden': hidden,
                    'timeout': 30000
                })
            #Wait options
            response_html = await page.content()
            service_url = action_request.url

            puppeteer_html_response = PuppeteerHtmlResponse(service_url,
                                        puppeteer_request,
                                        context_id = context_id,
                                        page_id = page_id,
                                        html = response_html,
                                        cookies=cookies)
            return puppeteer_html_response
        return syncer.sync(async_click())




    def go_back(self, action_request: ActionRequest):
        puppeteer_request = action_request.meta.get("puppeteer_request")
        context_id, page_id = syncer.sync(self.context_manager.check_context_and_page(puppeteer_request.context_id, puppeteer_request.page_id))
        page = self.context_manager.get_page_by_id(context_id, page_id)

        async def async_go_back():
            cookies = action_request.cookies

            await page.goBack()

            #Wait options
            wait_options = action_request.action.payload().get("waitOptions", {}) or {}
            timeout = wait_options.get("selectorOrTimeout", 1000)
            visible = wait_options.get("visible", False)
            hidden = wait_options.get("hidden", False)

            if isinstance(timeout, (int, float)):
                await asyncio.sleep(timeout / 1000)
            else:
                await page.waitFor(selector=timeout, options={
                    'visible': visible,
                    'hidden': hidden,
                    'timeout': 30000
                })
            #Wait options

            response_html = await page.content()
            service_url = action_request.url
            puppeteer_html_response = PuppeteerHtmlResponse(service_url,
                                        puppeteer_request,
                                        context_id = context_id,
                                        page_id = page_id,
                                        html = response_html,
                                        cookies=cookies)

            return puppeteer_html_response

        return syncer.sync(async_go_back())


    def go_forward(self, action_request: ActionRequest):
        puppeteer_request = action_request.meta.get("puppeteer_request")
        context_id, page_id = syncer.sync(self.context_manager.check_context_and_page(puppeteer_request.context_id, puppeteer_request.page_id))
        page = self.context_manager.get_page_by_id(context_id, page_id)

        async def async_go_forward():
            cookies = action_request.cookies

            await page.goForward()

            #Wait options
            wait_options = action_request.action.payload().get("waitOptions", {}) or {}
            timeout = wait_options.get("selectorOrTimeout", 1000)
            visible = wait_options.get("visible", False)
            hidden = wait_options.get("hidden", False)

            if isinstance(timeout, (int, float)):
                await asyncio.sleep(timeout / 1000)
            else:
                await page.waitFor(selector=timeout, options={
                    'visible': visible,
                    'hidden': hidden,
                    'timeout': 30000
                })
            #Wait options

            response_html = await page.content()
            service_url = action_request.url
            puppeteer_html_response = PuppeteerHtmlResponse(service_url,
                                        puppeteer_request,
                                        context_id = context_id,
                                        page_id = page_id,
                                        html = response_html,
                                        cookies=cookies)

            return puppeteer_html_response

        return syncer.sync(async_go_forward())



    def screenshot(self, action_request: ActionRequest):
        puppeteer_request = action_request.meta.get("puppeteer_request")
        context_id, page_id = syncer.sync(self.context_manager.check_context_and_page(puppeteer_request.context_id, puppeteer_request.page_id))
        page = self.context_manager.get_page_by_id(context_id, page_id)

        async def async_screenshot():
            cookies = action_request.cookies

            request_options = action_request.action.options or {}
            screenshot_options = {'encoding': 'binary'}
            screenshot_options.update(request_options)

            screenshot_bytes = await page.screenshot(screenshot_options)
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')


            service_url = action_request.url

            puppeteer_screenshot_response = PuppeteerScreenshotResponse(service_url,
                                        puppeteer_request,
                                        context_id = context_id,
                                        page_id = page_id,
                                        screenshot = screenshot_base64)

            return puppeteer_screenshot_response

        return syncer.sync(async_screenshot())


    '''
    class PuppeteerScreenshotResponse(PuppeteerResponse):
        """
        Response for Screenshot action.
        Screenshot is available via self.screenshot as base64 encoded string.
        """

        attributes: Tuple[str, ...] = PuppeteerResponse.attributes + ("screenshot",)

        def __init__(self, url, puppeteer_request, context_id, page_id, **kwargs):
            self.screenshot = kwargs.pop("screenshot")
            super().__init__(url, puppeteer_request, context_id, page_id, **kwargs)


    class PuppeteerHtmlResponse(PuppeteerResponse):
        """
        scrapy.TextResponse capturing state of a page in browser.
        Additionally, exposes received html and cookies via corresponding attributes.
        """

        attributes: Tuple[str, ...] = PuppeteerResponse.attributes + ("html", "cookies")
        """
            A tuple of :class:`str` objects containing the name of all public
            attributes of the class that are also keyword parameters of the
            ``__init__`` method.

            Currently used by :meth:`PuppeteerResponse.replace`.
        """

        def __init__(self, url, puppeteer_request, context_id, page_id, **kwargs):
            self.html = kwargs.pop("html")
            self.cookies = kwargs.pop("cookies")
            kwargs.setdefault("body", self.html)
            kwargs.setdefault("encoding", "utf-8")
            kwargs.setdefault("headers", {}).setdefault("Content-Type", "text/html")
            super().__init__(url, puppeteer_request, context_id, page_id, **kwargs)

    '''

























    '''
    def get_page_html(self):
        html_code = syncer.sync(self.page.content())
        return html_code

    def make_and_save_screen(self):
        syncer.sync(self.page.screenshot({'path': f'/home/andrew/Documents/screenshots/example{random.randint(1000, 9999)}.png', 'fullPage': True}))

    def go_back(self, action_request: ActionRequest):
        #url = action_request.action.payload()["url"]
        service_url = action_request.url
        puppeteer_request = action_request.meta.get("puppeteer_request")
        cookies = action_request.cookies
        syncer.sync(self.page.goBack())
        response_html = self.get_page_html()

        PHR = PuppeteerHtmlResponse(service_url,
                                    puppeteer_request,
                                    context_id = "",
                                    page_id = "",
                                    html = f"{response_html}",
                                    cookies=cookies)

        return PHR

        def go_forward(self, action_request: ActionRequest):
        #url = action_request.action.payload()["url"]
        service_url = action_request.url
        puppeteer_request = action_request.meta.get("puppeteer_request")
        cookies = action_request.cookies
        syncer.sync(self.page.goForward())



        response_html = self.get_page_html()

        PHR = PuppeteerHtmlResponse(service_url,
                                    puppeteer_request,
                                    context_id = "",
                                    page_id = "",
                                    html = f"{response_html}",
                                    cookies=cookies)

        return PHR



    #Обернуть также как goto
    def goto(self, action_request: ActionRequest):
        url = action_request.action.payload()["url"]
        service_url = action_request.url
        puppeteer_request = action_request.meta.get("puppeteer_request")
        cookies = action_request.cookies
        self.open_page(url)
        response_html = self.get_page_html()

        PHR = PuppeteerHtmlResponse(service_url,
                                    puppeteer_request,
                                    context_id = "",
                                    page_id = "",
                                    html = f"{response_html}",
                                    cookies=cookies)

        return PHR


#wait_options = action_request.action.payload().get("waitOptions", None)
        def screen_s(self):
        syncer.sync(self.page.screenshot({'path': f'/home/andrew/Documents/screenshots/example{random.randint(1000, 9999)}.png', 'fullPage': True}))

    def click(self, action_request: ActionRequest):

        selector = action_request.action.payload()["selector"]
        wait_options = None
        if "waitOptions" in action_request.action.payload():
            wait_options = action_request.action.payload()["waitOptions"]
            print(wait_options)

        #time.sleep(2)

        syncer.sync(self.page.click(selector))

        #time.sleep(2)

        #self.page.waitForSelector(selector, {'timeout': 30000})

        response_html = self.get_page_html()
        service_url = action_request.url
        puppeteer_reqiest = PuppeteerRequest(service_url, close_page=False)
        #
        PHR = PuppeteerHtmlResponse(service_url,
                                    puppeteer_reqiest,
                                    "page_ID",
                                    "contex_id",
                                    html=f"{response_html}",
                                    cookies=self.page.cookies())
        return PHR


    '''

    '''


    '''




'''




    def goto_data(self, action_request: ActionRequest):
        data = []
        data.append(action_request.action.payload()["url"])
        puppeteer_reqiest = PuppeteerRequest('https://demo-site.at.ispras.ru/ajax/computers/laptops', close_page=False)
        data.append(puppeteer_reqiest)
        return data




    def data_for_PyP(self, ar: ActionRequest):
        service_url = ar.url
        endpoint = ar.action.endpoint
        action_payload = ar.action.payload()
        if "url" in action_payload:
            print(action_payload["url"])




    def print_all_data(self, ar: ActionRequest):
        data_array = []
        data_array.append("Data from request")
        data_array.append(f"url: {ar.url}")
        data_array.append(f"action endpoint: {ar.action.endpoint}")
        data_array.append(f"action payload: {ar.action.payload()}")
        data_array.append(f"headers: {ar.headers}")
        data_array.append(f"body: {ar.body}")
        data_array.append(f"cookies: {ar.cookies}")
        data_array.append(f"dont_filter: {ar.dont_filter}")
        data_array.append(f"callback: {ar.callback}")
        data_array.append(f"cb_kwargs: {ar.cb_kwargs}")
        data_array.append(f"errback: {ar.errback}")
        data_array.append(f"meta: {ar.meta}")
        data_array.append(f"flags: {ar.flags}")
        data_array.append(f"encoding: {ar.encoding}")
        data_array.append(f"__repr__: {ar.__repr__()}")

        return data_array


    def get_all_from_action_request(self, ar: ActionRequest):
        meta = ar.meta
        body = ar.body
        cookies = ar.cookies
        url = ar.url
        act = ar.action.endpoint

        return f"{meta}\n\n\n{body}\n\n\n{ar.action.payload()}\n{cookies}\n{url}\n{act}"


    def process_puppeteer_request(self, request: PuppeteerRequest):
        cookies_data = {"session": "abcdef123456"}
        service_url = request.url

        PHR = PuppeteerHtmlResponse(service_url,
                                    request,
                                    "page_ID",
                                    "contex_id",
                                    html = f"b'{d}'", #Тут явно должен быть ответ другой   #f"b'{d}'" #first_line,
                                    cookies=cookies_data)
        #print(first_line)
        #PHR.replace(body=first_line)
        return PHR

        AR = ActionRequest(
            url=service_url,
            action=action,
            method="POST",
            headers=Headers({"Content-Type": action.content_type}),
            body=self._serialize_body(action, request),
            dont_filter=True,
            cookies=request.cookies,
            priority=request.priority,
            callback=request.callback,
            cb_kwargs=request.cb_kwargs,
            errback=request.errback,
            meta=meta,
        )

class BrowserManager:
    def __init__(self):
        self.browser = None
        self.page = None
        self.in_br()
        self.in_page()

    async def _in_br(self):
        self.browser = await launch()
        return True

    def in_br(self):
        asyncio.run(self._in_br())
        return True

    async def _in_page(self):
        self.page = await self.browser.newPage()
        return True

    def in_page(self):
        asyncio.run(self._in_page())
        return True

    async def _open_page(self, url):
        await self.page.goto(url)
        return True

    def open_page(self, url):
        asyncio.run(self._open_page(url))
        return True
        #return# self.loop.run_until_complete(self._open_page(url))

    async def _get_page_html(self):
        html_code = await self.page.content()

        return html_code

    def get_page_html(self):
        html_code = asyncio.run(self._get_page_html())

        return html_code





class BrowserManager2:
    def __init__(self):
        """
        Инициализирует BrowserManager, запускает браузер и открывает новую пустую страницу.
        """
        self.browser = None
        self.page = None
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._initialize_browser())

    async def _initialize_browser(self):
        """Запускает браузер и открывает новую пустую страницу."""
        self.browser = await launch(headless=True)  # headless=True для работы в фоновом режиме
        self.page = await self.browser.newPage()

    async def _open_page(self, url):
        """Асинхронный метод для открытия страницы."""
        if self.page is None:
            raise RuntimeError("Браузер не инициализирован.")
        await self.page.goto(url)

    async def _get_page_html(self):
        """Асинхронный метод для получения HTML-кода страницы."""
        if self.page is None:
            raise RuntimeError("Браузер не инициализирован.")
        return await self.page.content()

    def open_page(self, url):
        """
        Открывает страницу по указанному URL.
        :param url: URL страницы.
        out = await asyncio.gather(*[one_call(url) for url in urls])
        return out
        """
        asyncio.run(self._open_page(url))
        #return# self.loop.run_until_complete(self._open_page(url))

    def get_page_html(self):
        """
        Возвращает HTML-код текущей страницы.
        :return: HTML-код страницы.
        """
        return "Page HTML"#self.loop.run_until_complete(self._get_page_html())

    def fetch_html(self, url):
        """
        Открывает страницу по URL и возвращает её HTML-код.
        :param url: URL страницы.
        :return: HTML-код страницы.
        """
        self.open_page(url)  # Открываем страницу
        return self.get_page_html()  # Получаем HTML-код

    def close_browser(self):
        """
        Закрывает браузер.
        """
        if self.browser:
            self.loop.run_until_complete(self.browser.close())

    def __del__(self):
        """Закрывает браузер при уничтожении объекта."""
        self.close_browser()

'''
