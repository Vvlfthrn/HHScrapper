import json
import logging
import time
import os

from django.db import transaction
from django.db.models import Count, Q
from django.template import Template, Context
from langchain_ollama import ChatOllama
from langchain_core.callbacks.manager import CallbackManager
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage

from django.core.management import BaseCommand

from hhscrapper.app.models import LLMEnum, LLMResult, VacancyPromptDecision, DecisionState

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
    all_llm_tasks_done = VacancyPromptDecision.objects.filter(state=DecisionState.ALL_TASKS_EXECUTED).values_list('id', flat=True)

    for vpd in VacancyPromptDecision.objects.filter(id__in=all_llm_tasks_done, koef__isnull=True).annotate(
        cor_count=Count('llm_results', filter=Q(llm_results__corresponds=True)), llm_cnt=Count('llm_results')
    ).prefetch_related('prompt', 'vacancy'):
        vpd.koef = vpd.cor_count / vpd.llm_cnt
        vpd.consensus = vpd.cor_count == vpd.llm_cnt
        vpd.state = DecisionState.CONSENSUS_CHECKED
        vpd.save(update_fields=['koef', 'consensus', 'state'])
        logger.info(f'Consensus (vacancy/prompt/koef):{vpd.vacancy.title}/{vpd.prompt.title}/{vpd.koef}')


def fill_result_from_db(r: LLMResult, already_completed: LLMResult):
    r.corresponds = already_completed.corresponds
    r.comment = already_completed.comment
    r.extra = already_completed.extra
    r.execution_done = True
    return r


def fill_from_llm(r: LLMResult, chat_model: ChatOllama):
    messages = [
        SystemMessage(
            content=r.prompt.sys_template
        ),
        HumanMessage(
            content=Template(r.prompt.human_template).render(
                Context(
                    {
                        'TITLE': r.vacancy.title,
                        'WORK_EXP': r.vacancy.work_experience,
                        'DESC': r.vacancy.description,
                        'SKILLS': r.vacancy.skills.all(),
                    }
                )
            ))
    ]

    response = chat_model.invoke(messages)

    logger.debug(f'Model response:\n{response.content}')
    try:
        d = json.loads(remove_think_tag(response.content))
        if 'corresponds' in d:
            r.corresponds = d.get('corresponds')
            r.comment = d.get('comment', None)
            r.extra = d.get('extra', None)
        else:
            r.extra = response.content
    except Exception as e:
        r.comment = str(e)
        r.extra = response.content
    r.execution_done = True
    return r


def llm_do_work():
    for model in LLMEnum:
        query = LLMResult.objects.filter(llm=model.value, execution_done=False)
        counter = 0
        total = query.count()
        if total:
            chat_model = ChatOllama(
                model=model.label, base_url=LLM_URL, format=None if model == LLMEnum.QWEN else 'json',
                callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]),
                validate_model_on_init=True,
                temperature=0.0,
                client_kwargs={"timeout": REQUEST_TIMEOUT}
            )
            for r in query.prefetch_related('vacancy__skills', 'prompt'):
                counter += 1
                already_completed = LLMResult.objects.filter(task_hash=r.get_hash(), execution_done=True).first()

                if already_completed:
                    logger.info(f'From DB {model.label} {counter}/{total} {r.vacancy.url}')
                    fill_result_from_db(r, already_completed)
                else:
                    logger.info(f'From LLM {model.label} {counter}/{total} {r.vacancy.url}')
                    fill_from_llm(r, chat_model)
                with transaction.atomic():
                    r.save()
                    for decision in r.decisions.filter(state=DecisionState.READY_TO_EXECUTE):
                        if not decision.llm_results.filter(execution_done=False).exists():
                            decision.state = DecisionState.ALL_TASKS_EXECUTED
                            decision.save(update_fields=['state'])
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
