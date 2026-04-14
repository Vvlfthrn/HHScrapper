import json
import logging
import time
import os

from django.db.models import Count
from langchain_ollama import ChatOllama
from langchain_core.callbacks.manager import CallbackManager
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage

from django.core.management import BaseCommand

from hhscrapper.app.models import LLMEnum, Vacancy, LLMResult
from hhscrapper.prompts import RESUME, PROMPT

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

REQUEST_TIMEOUT = float(os.environ['LLM_REQUEST_TIMEOUT'])
LLM_URL = os.environ['LLM_URL']
LLM_PERIOD = int(os.environ['LLM_PERIOD'])


def remove_think_tag(response:str):
    result = response.find('</think>')
    if result != -1:
        response = response[result+8:].strip()
    return response


def check_consensus():
    llm_tasks_count = len(LLMEnum)
    all_llm_tasks_done = Vacancy.objects.annotate(
        cnt=Count('llm_results')).filter(notified=False, cnt=llm_tasks_count).values_list('id', flat=True)
    for vac in Vacancy.objects.filter(id__in=all_llm_tasks_done, llm_results__corresponds=True).annotate(
        cor_count=Count('llm_results')):
        vac.koef = vac.cor_count / float(llm_tasks_count)
        vac.consensus = vac.cor_count == llm_tasks_count
        vac.save()


def llm_do_work():
    for model in LLMEnum:
        chat_model = ChatOllama(
            model=model.label, base_url=LLM_URL, format=None if model == LLMEnum.QWEN else 'json',
            callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]),
            validate_model_on_init=True,
            temperature=0.0,
            client_kwargs={"timeout": REQUEST_TIMEOUT}
        )
        query = Vacancy.objects.filter(
                notified=False
        ).exclude(
            id__in=Vacancy.objects.filter(
                notified=False,
                llm_results__llm=model.value
            ))
        counter = 0
        total = query.count()
        for vac in query.prefetch_related('skills'):
            counter += 1
            logger.info(f'{model.label} {counter}/{total} {vac.url}')
            messages = [
                SystemMessage(
                    content=PROMPT
                    ),
                HumanMessage(
                    content=RESUME +
                            f'\n\n'
                            f'ВАКАНСИЯ:'
                            f'\tДолжность: {vac.title}\n'
                            f'\t{vac.work_experience}'
                            f'\tОписание:{vac.description}'
                            f'\tНавыки:{",".join(x.title for x in vac.skills.all())}'
                            ),
            ]

            response = chat_model.invoke(messages)

            logger.debug(f'Model response:\n{response.content}')
            result = LLMResult(vacancy=vac, llm=model.value)
            try:
                d = json.loads(remove_think_tag(response.content))
                if 'corresponds' in d:
                    result.corresponds = d.get('corresponds')
                    result.comment = d.get('comment', None)
                    result.extra = d.get('extra', None)
                else:
                    result.extra = response.content
            except Exception as e:
                result.comment = str(e)
                result.extra = response.content
            result.save()
    check_consensus()



class Command(BaseCommand):
    help = "Run llm's"

    def handle(self, *args, **options):
        while True:
            try:
                llm_do_work()
            except KeyboardInterrupt:
                break
            time.sleep(LLM_PERIOD)
