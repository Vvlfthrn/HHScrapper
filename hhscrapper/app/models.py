from django.db import models


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
    vacancy = models.ForeignKey('Vacancy', on_delete=models.CASCADE, related_name='llm_results')

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
    consensus = models.BooleanField(null=True, blank=True)
    koef = models.FloatField(blank=True, null=True, db_index=True)
    notified = models.BooleanField(default=False, db_index=True)
    load_dt = models.DateTimeField(null=True)
    start_url = models.URLField(blank=True, null=True)


    class Meta:
        verbose_name_plural = "Vacancies"
        verbose_name = "Vacancy"

    def __str__(self):
        return f'{self.hh_id}: {self.title}'
