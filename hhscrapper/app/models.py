from django.db import models
from django.db.models import Value, F
from django.db.models.functions import Lower


class LLMEnum(models.IntegerChoices):
    LLAMA31 = 1,    'llama3.1'
    DEEPSEEK = 2,   'deepseek-r1:14b'
    GEMMA = 3,      'gemma3:12b'
    QWEN = 4,       'qwen3:14b'
    PHI = 5,        'phi4:14b'


class LLMResult(models.Model):
    llm = models.IntegerField(choices=LLMEnum)
    corresponds = models.BooleanField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    extra = models.TextField(blank=True, null=True)
    prompt = models.ForeignKey('Prompt', on_delete=models.CASCADE, related_name='llm_results', null=True)
    vacancy = models.ForeignKey('Vacancy', on_delete=models.CASCADE, related_name='llm_results', null=True)
    execution_done = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "LLM Results"
        verbose_name = "LLM Result"

    def __str__(self):
        return f'{self.get_llm_display()}: {self.corresponds}'


class Skill(models.Model):
    title = models.TextField(unique=True)

    class Meta:
        verbose_name_plural = "Skills"
        verbose_name = "Skill"

    def __str__(self):
        return self.title


class Vacancy(models.Model):
    hh_id = models.IntegerField(db_index=True)
    url = models.URLField()
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    salary = models.TextField(blank=True, null=True)
    compensation = models.TextField(blank=True, null=True)
    work_experience = models.TextField(blank=True, null=True)
    common_employment = models.TextField(blank=True, null=True)
    hiring_format = models.TextField(blank=True, null=True)
    work_schedule = models.TextField(blank=True, null=True)
    work_hours = models.TextField(blank=True, null=True)
    work_format = models.TextField(blank=True, null=True)
    skills = models.ManyToManyField(Skill, related_name="vacancies")
    load_dt = models.DateTimeField(null=True)
    start_url = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Vacancies"
        verbose_name = "Vacancy"

    def __str__(self):
        return f'{self.hh_id}: {self.title}'


class StopWord(models.Model):
    title = models.TextField(unique=True)

    class Meta:
        verbose_name_plural = "Stop Words"
        verbose_name = "Stop Word"

    def __str__(self):
        return self.title


class Prompt(models.Model):
    title = models.TextField('Title')
    sys_template = models.TextField(blank=True, null=True)
    human_template = models.TextField('Template', blank=True, null=True,
                                help_text='You may use template tags for rendering.'
                                          'Available tags are {{TITLE}} '
                                          '{{WORK_EXP}} {{DESC}} {{SKILLS}}')
    stop_words = models.ManyToManyField(StopWord, related_name='prompts')

    class Meta:
        verbose_name_plural = "Prompts"
        verbose_name = "Prompt"

    def vacancy_with_stop_words(self, vacancy: Vacancy):
        return self.stop_words.annotate(
            lo=Lower('title'),
            v_title=Value(vacancy.title.lower(), output_field=models.TextField())
        ).filter(
            v_title__icontains=F('lo')
        ).exists()

    def __str__(self):
        return self.title


class ExecuteLLM(models.Model):
    title = models.TextField('Title')
    llm = models.IntegerField(choices=LLMEnum, unique=True)

    class Meta:
        verbose_name_plural = "Execute LLMs"
        verbose_name = "Execute LLM"

    def __str__(self):
        return self.title


class SearchQueryPromptLink(models.Model):
    search_query = models.ForeignKey('SearchQuery', on_delete=models.CASCADE, related_name='search_links')
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name='prompt_links')
    llms = models.ManyToManyField(ExecuteLLM, related_name="+")

    class Meta:
        verbose_name_plural = "Search Query Prompt Links"
        verbose_name = "Search Query Prompt Link"

    def __str__(self):
        return f'{self.search_query.title}: {self.prompt.title}'



class SearchQuery(models.Model):
    query = models.TextField('HHQuery', blank=True, null=True)
    title = models.TextField('Title', blank=True, null=True)
    prompts = models.ManyToManyField(Prompt, verbose_name='Prompts', related_name="search_queries", through=SearchQueryPromptLink)
    active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Search Queries"
        verbose_name = "Search Query"

    def __str__(self):
        return self.title

    @classmethod
    def active_prompts(cls):
        return cls.objects.filter(active=True)


class DecisionState(models.IntegerChoices):
    CREATED = 1, 'Created'
    READY_TO_EXECUTE = 2, 'Ready to Execute'
    ALL_TASKS_EXECUTED = 3, 'ALL_TASKS_EXECUTED'
    DONE = 4, 'Done'
    CONSENSUS_CHECKED = 5, 'Consensus Checked'


class VacancyPromptDecision(models.Model):
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE)
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, null=True)
    consensus = models.BooleanField(null=True, blank=True, db_index=True)
    koef = models.FloatField(blank=True, null=True, db_index=True)
    notified = models.BooleanField(default=False, db_index=True)
    llm_results = models.ManyToManyField(LLMResult, related_name="decisions")
    state = models.IntegerField(choices=DecisionState, default=DecisionState.CREATED, db_index=True)

    class Meta:
        verbose_name_plural = "Vacancy Prompt Decisions"
        verbose_name = "Vacancy Prompt Decision"
        constraints = [
            models.UniqueConstraint(fields=['vacancy', 'prompt'], name='unique_vacancy_prompt_decision'),
        ]

    def __str__(self):
        return f'{self.vacancy.title}: {self.prompt.title if self.prompt else 'None'}'