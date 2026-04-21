import copy
import time

import asyncio
import logging

from telethon import TelegramClient
from django.core.management import BaseCommand
from django.db import transaction

from hhscrapper.app.models import Vacancy
from hhscrapper.app.telebot import API_ID, API_HASH, BOT_TOKEN, USER_ID, SLEEP_TIME

logger = logging.getLogger('asyncio')
logging.basicConfig(level=logging.INFO)


async def send_messages(vacancies:list):
    bot = TelegramClient('sender_bot.db', API_ID, API_HASH)
    client = await bot.start(bot_token=BOT_TOKEN)
    vacs = copy.copy(vacancies)
    while vacs:
        to_send = vacs[:8]
        vacs = vacs[8:]
        message = ''
        for vac in to_send:
            message += f'{vac.title} ({vac.koef})\n'
            message += f'https://hh.ru/vacancy/{vac.hh_id}\n'
            message += '===========\n\n'
        logger.info(f'Sending message to {USER_ID} vacs: {[x.id for x in to_send]}')
        await client.send_message(USER_ID, message=message)
        logger.info(f'Sleeping {SLEEP_TIME} seconds')
        await asyncio.sleep(SLEEP_TIME)
    await bot.disconnect()
    return True


def bot_do_work():
    query = Vacancy.objects.filter(notified=False, koef__gte=0.4)
    if query.exists():
        vacancies = [x for x in query.all()]
        if asyncio.run(send_messages(vacancies)):
            Vacancy.objects.filter(id__in=[x.id for x in vacancies]).update(notified=True)


class Command(BaseCommand):
    help = "Run telebot"

    def handle(self, *args, **options):
        while True:
            try:
                with transaction.atomic():
                    bot_do_work()
                time.sleep(30)
            except KeyboardInterrupt:
                break