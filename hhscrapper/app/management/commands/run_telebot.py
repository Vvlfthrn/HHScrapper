import copy
import time

import asyncio
import logging
from typing import Iterable

from telethon import TelegramClient
from django.core.management import BaseCommand
from django.db import transaction, models

from hhscrapper.app.models import VacancyPromptDecision, DecisionState
from hhscrapper.app.telebot import API_ID, API_HASH, BOT_TOKEN, USER_ID, SLEEP_TIME

logger = logging.getLogger('asyncio')
logging.basicConfig(level=logging.INFO)


async def send_messages(vacancy_decisions:Iterable[VacancyPromptDecision]):
    bot = TelegramClient('./hhscrapper/sender_bot.db', API_ID, API_HASH)
    client = await bot.start(bot_token=BOT_TOKEN)
    vacancy_decisions = [x async for x in VacancyPromptDecision.objects.filter(
        id__in=vacancy_decisions, koef__gte=models.F('prompt__koef')).select_related('vacancy', 'prompt')]
    offset = 8
    step = 0
    while vacs:=vacancy_decisions[offset * step:offset * (step + 1)]:
        message = ''
        for vd in vacs:
            message += f'{vd.vacancy.title} ({vd.koef})\n'
            message += f'https://hh.ru/vacancy/{vd.vacancy.hh_id}\n'
            message += f'Промпт: {vd.prompt.title}\n'
            message += '===========\n\n'
        logger.info(f'Sending message to {USER_ID} vacs: {[x.id for x in vacs]}')
        await client.send_message(USER_ID, message=message)
        for vd in vacs:
            vd.notified = True
            await vd.asave(update_fields=['notified'])
        logger.info(f'Sleeping {SLEEP_TIME} seconds')
        await asyncio.sleep(SLEEP_TIME)
        step += 1
    await bot.disconnect()
    return True


def bot_do_work():
    query = VacancyPromptDecision.objects.filter(state=DecisionState.CONSENSUS_CHECKED)
    if query.exists():
        vacancy_decisions = query.values_list('id', flat=True)
        if asyncio.run(send_messages(vacancy_decisions)):
            VacancyPromptDecision.objects.filter(id__in=vacancy_decisions).update(state=DecisionState.DONE)


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