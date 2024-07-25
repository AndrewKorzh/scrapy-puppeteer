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
