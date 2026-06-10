import os
import ssl
import time
import smtplib
import asyncio
import logging
from email.message import EmailMessage
from typing import Iterable

from telethon import TelegramClient
from django.core.management import BaseCommand
from django.db import transaction, models

from hhscrapper.app.models import VacancyPromptDecision, DecisionState
from hhscrapper.app.telebot import API_ID, API_HASH, BOT_TOKEN, USER_ID, SLEEP_TIME

SENDER_EMAIL = os.environ.get('SENDER_EMAIL', None)
APP_PASSWORD = os.environ.get('APP_PASSWORD', None)
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', None)

logger = logging.getLogger('asyncio')
logging.basicConfig(level=logging.INFO)


def get_vacancy_description(vd: VacancyPromptDecision):
    description = ''
    description += f'{vd.vacancy.title} ({vd.koef})\n'
    description += f'https://hh.ru/vacancy/{vd.vacancy.hh_id}\n'
    description += f'Промпт: {vd.prompt.title}\n'
    description += '===========\n\n'
    return description

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
            message += get_vacancy_description(vd)
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


def send_message_by_email(vacancy_decisions):
    if not SENDER_EMAIL:
        return False

    vacancies = VacancyPromptDecision.objects.filter(
        id__in=vacancy_decisions, koef__gte=models.F('prompt__koef')).select_related('vacancy', 'prompt')
    message = ''
    for vd in vacancies:
        message += get_vacancy_description(vd)

    email = EmailMessage()
    email['From'] = SENDER_EMAIL
    email['To'] = RECEIVER_EMAIL
    email['Subject'] = 'New vacancies'
    email.set_content(message)
    logger.info(f'Sending message to {USER_ID} vacs: {[x.id for x in vacancies]}')

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(email)
            logger.info(f'Send message successful')
            for vd in vacancies:
                vd.notified = True
                vd.save(update_fields=['notified'])
            return True
    except smtplib.SMTPException as e:
        logger.error(e)
        return False


def bot_do_work():
    query = VacancyPromptDecision.objects.filter(state=DecisionState.CONSENSUS_CHECKED)
    if query.exists():
        vacancy_decisions = query.values_list('id', flat=True)
        if (
                asyncio.run(send_messages(vacancy_decisions)) or
                send_message_by_email(vacancy_decisions)
        ):
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