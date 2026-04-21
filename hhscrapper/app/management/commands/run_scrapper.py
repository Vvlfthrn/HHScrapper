import json
import os
import time
from datetime import datetime, timedelta

import httpx
import pytz
import logging
import re
import asyncio

from django.core.management.base import BaseCommand
from django.db import transaction

from selenium.common import InvalidCookieDomainException
from seleniumbase import SB
from seleniumbase.common.exceptions import NoSuchElementException

from hhscrapper.app import telebot
from hhscrapper.app.models import Vacancy, Skill

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

VAC_ID_FINDER = re.compile(r'https://[a-zA-Z0-9_-]*\.*hh.ru/vacancy/(\d+)')

WAIT_TIMEOUT = 10
DELAY_TIMEOUT = 3
PAGE_LOAD_TIMEOUT = 30
CAPTCHA_LOADING_TIMEOUT = 20
TM0 = 0
SWITCH_WINDOW_TIMEOUT = 3
VAC_READ_TIMEOUT = 2
NEXT_LIST_PAGE_TIMEOUT = 5
WORKING_HOURS_PERIOD = 20 * 60
HOUR_PERIOD = 60 * 60
NETWORK_ERROR_PERIOD = 5 * 60

SEARCH_STR = json.loads(os.environ['HH_QUERIES'])
LOGIN = os.environ['HH_LOGIN']
PASSWORD = os.environ['HH_PASS']

VACANCIES_LIST_SELECTOR='div:is([data-qa="vacancy-serp__vacancy"], [data-qa="vacancy-serp__vacancy vacancy-serp-item_clickme"]) a[data-qa="serp-item__title"]'
NEXT_PAGE_SELECTOR = 'nav[data-qa="pager-block"] li:has(a[aria-current="true"]) + li:has(a[aria-current="false"])'


def solve_captha(sb:SB):
    sb.save_screenshot('captcha.png', selector='img[data-qa="account-captcha-picture"]')
    captcha_text = asyncio.run(telebot.send_captcha())
    if captcha_text:
        sb.type('input[data-qa="account-captcha-input"]', text=captcha_text)
        sb.click('button[type="submit"]', delay=DELAY_TIMEOUT)


def login(sb:SB):
    sb.sleep(VAC_READ_TIMEOUT)
    sb.assert_element('button[data-qa="submit-button"]', timeout=WAIT_TIMEOUT)
    sb.assert_text('Войти', 'button[data-qa="submit-button"] span', timeout=WAIT_TIMEOUT)
    sb.click('button[data-qa="submit-button"] span:contains("Войти")', delay=DELAY_TIMEOUT)
    sb.assert_element('div[data-qa="credential-type-switch"', timeout=WAIT_TIMEOUT)
    sb.assert_element('input[data-qa="credential-type-PHONE checked"]', timeout=WAIT_TIMEOUT)
    sb.assert_element('input[data-qa="magritte-phone-input-national-number-input"][inputmode="tel"]',
                      timeout=WAIT_TIMEOUT)
    sb.type('input[data-qa="magritte-phone-input-national-number-input"][inputmode="tel"]', text=LOGIN,
            timeout=WAIT_TIMEOUT)

    sb.assert_element('button[data-qa="expand-login-by-password"]', timeout=WAIT_TIMEOUT)
    sb.click('button[data-qa="expand-login-by-password"]', delay=DELAY_TIMEOUT)
    sb.assert_element('input[name="password"][type="password"]', timeout=WAIT_TIMEOUT)
    sb.type('input[name="password"][type="password"]', text=PASSWORD)
    sb.click('button[data-qa="submit-button"] span:contains("Войти")', delay=DELAY_TIMEOUT)
    time.sleep(CAPTCHA_LOADING_TIMEOUT)
    # manual solve captcha
    captcha = sb.find_elements(
            'div[data-qa^="modal-header"] h2[data-qa="title"]:contains("Пройдите капчу")')
    if captcha:
        solve_captha(sb)
    # REDIRECT TO https://hh.ru/?role=applicant
    sb.assert_element('span[data-qa="mainmenu_profileAndResumes"]', timeout=WAIT_TIMEOUT)
    sb.save_cookies()
    return True

def get_element_text(sb: SB, selector:str, separator: str = ', ', only_first: bool = False):
    result = ''
    try:
        if only_first:
            result = sb.find_element(selector).text
        else:
            result = separator.join(x.text for x in sb.find_elements(selector))
    except NoSuchElementException:
        pass
    return result

def parse(sb: SB, timestamp:datetime = None, vac_id :str = None):
    v = Vacancy(
        hh_id=int(vac_id),
        url=sb.get_current_url(),
        title= get_element_text(sb, 'div[class="vacancy-title"] h1[data-qa="vacancy-title"] span', separator=''),
        salary=get_element_text(sb, 'div[data-qa="vacancy-salary"] span', only_first=True),
        compensation=get_element_text(sb, 'p[data-qa="compensation-frequency-text"]'),
        work_experience=get_element_text(sb, 'p[data-qa="work-experience-text"]'),
        common_employment=get_element_text(sb, 'div[data-qa="common-employment-text"]'),
        hiring_format=get_element_text(sb, 'div[data-qa="vacancy-hiring-formats"]'),
        work_schedule=get_element_text(sb, 'p[data-qa="work-schedule-by-days-text"]'),
        work_hours=get_element_text(sb, 'div[data-qa="working-hours-text'),
        work_format=get_element_text(sb, 'p[data-qa="work-formats-text"]'),
        description=get_element_text(
            sb, 'div[class="vacancy-description"] div[data-qa="vacancy-description"]'),
        notified=False,
        load_dt=timestamp,
    )
    with transaction.atomic():
        v.save()
        for x in sb.find_elements('ul[class^="vacancy-skill-list"] li[data-qa="skills-element"]'):
            s, _ = Skill.objects.get_or_create(title=x.text.strip())
            v.skills.add(s)
    return v

def do_work():

    with SB(
        uc=True,
        test=False,
        locale="ru",
        window_size='1920,1080',
        ) as sb:
        try:
            timestamp = datetime.now()
            url = SEARCH_STR[0]
            sb.uc_open_with_reconnect(url)
            sb.wait_for_ready_state_complete(timeout=PAGE_LOAD_TIMEOUT)
            try:
                sb.load_cookies()
            except FileNotFoundError:
                 pass

            url = SEARCH_STR[0]
            sb.uc_open_with_reconnect(url)
            sb.wait_for_ready_state_complete(timeout=PAGE_LOAD_TIMEOUT)

            if sb.find_elements('a[data-qa="login"]'):
                sb.open_url("https://hh.ru/account/login?role=applicant")
                sb.wait_for_ready_state_complete(timeout=PAGE_LOAD_TIMEOUT)
                login(sb)
            for search_query in SEARCH_STR:
                sb.open_url(search_query)
                sb.wait_for_ready_state_complete(timeout=PAGE_LOAD_TIMEOUT)
                logger.info(f'Opened {search_query}')
                while True:
                    links = sb.find_elements(VACANCIES_LIST_SELECTOR)
                    vac_new_links = set()
                    for x in links:
                        href = x.get_attribute('href')
                        found = VAC_ID_FINDER.findall(href)
                        if found and found[0] and Vacancy.objects.filter(hh_id=int(found[0])).exists():
                            pass
                        else:
                            vac_new_links.add(href)
                    logger.info(f'New links {len(vac_new_links)}')
                    for url in vac_new_links:
                        logger.info(f'Clicking {url}')
                        sb.click(VACANCIES_LIST_SELECTOR + f'[href="{url}"]')
                        sb.switch_to_window(1, timeout=SWITCH_WINDOW_TIMEOUT)
                        # time.sleep(SWITCH_WINDOW_TIMEOUT)
                        if sb.get_current_url().startswith('https://hh.ru/account/captcha'):
                            solve_captha(sb)
                        sb.wait_for_ready_state_complete(timeout=PAGE_LOAD_TIMEOUT)
                        vac_id = VAC_ID_FINDER.findall(sb.get_current_url())
                        logger.info(f'Found {vac_id}')
                        if vac_id and vac_id[0] and not Vacancy.objects.filter(hh_id=int(vac_id[0])).exists():
                            logger.info('Parsing page...')
                            parse(sb, timestamp=timestamp, vac_id=vac_id[0])
                            sb.scroll_to_bottom()
                            time.sleep(VAC_READ_TIMEOUT)
                        sb.driver.close()
                        sb.switch_to_window(0, timeout=SWITCH_WINDOW_TIMEOUT)
                    next_page = sb.find_elements(NEXT_PAGE_SELECTOR)
                    if not next_page:
                        logger.info(f'That was last page. Exiting...')
                        break
                    sb.click(NEXT_PAGE_SELECTOR, delay=DELAY_TIMEOUT)
                    time.sleep(NEXT_LIST_PAGE_TIMEOUT)
                    sb.wait_for_ready_state_complete(timeout=PAGE_LOAD_TIMEOUT)
                    logger.info(f'Loaded next page')
            sb.save_cookies()
            sb.driver.quit()
        except NoSuchElementException as e:
            sb.save_screenshot('./downloaded_files/screenshot.png')
            raise e

class Command(BaseCommand):
    help = "Run scrapper"

    def handle(self, *args, **options):
        while True:
            try:
                do_work()
                dt = datetime.now(tz=pytz.timezone('Europe/Moscow'))
                if 9 <= dt.hour <= 18 and dt.weekday() in range(5):
                    logger.info(f'Sleeping 20 min. . Next run in {dt + timedelta(seconds=WORKING_HOURS_PERIOD)}')
                    time.sleep(WORKING_HOURS_PERIOD)
                else:
                    logger.info(f'Sleeping 1 hour. Next run in {dt + timedelta(seconds=HOUR_PERIOD)}')
                    time.sleep(HOUR_PERIOD)
            except (InvalidCookieDomainException, httpx.ReadError) as e:
                logger.error(e)
                time.sleep(NEXT_LIST_PAGE_TIMEOUT)
            except KeyboardInterrupt:
                break