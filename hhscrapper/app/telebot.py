import logging
import os

from telethon import TelegramClient

API_ID = int(os.environ['TG_API_ID'])
API_HASH = os.environ['TG_API_HASH']
BOT_TOKEN = os.environ['TG_BOT_TOKEN']
CONVERSATION_TIMEOUT = int(os.environ['TG_CONVERSATION_TIMEOUT'])
USER_ID=os.environ['TG_USER_ID']

SLEEP_TIME = 3

logger = logging.getLogger('asyncio')
logging.basicConfig(level=logging.INFO)

async def send_captcha():
    result = ''
    bot = TelegramClient('bot.db', API_ID, API_HASH)
    client = await bot.start(bot_token=BOT_TOKEN)
    async with client.conversation(USER_ID, timeout=CONVERSATION_TIMEOUT) as conv:
        await conv.send_message('We have captcha moment :)')
        await conv.send_file('captcha.png')
        response = await conv.get_response()
        if response:
            result = response.raw_text
    await bot.disconnect()
    return result
