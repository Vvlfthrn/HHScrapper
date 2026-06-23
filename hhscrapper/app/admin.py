from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from hhscrapper.app.models import Vacancy, LLMResult, Prompt, SearchQuery, VacancyPromptDecision, SearchQueryPromptLink, \
    ExecuteLLM, StopWord


class SkillInlineAdmin(admin.TabularInline):
    model = Vacancy.skills.through


class StopWordInlineAdmin(admin.TabularInline):
    model = Prompt.stop_words.through


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'url', 'load_dt')
    readonly_fields = (
        'hh_id', 'url', 'title', 'description', 'salary', 'compensation',
        'work_experience', 'common_employment', 'hiring_format', 'work_schedule',
        'work_hours', 'work_format', 'load_dt', 'start_url', 'skills'
    )


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    autocomplete_fields = ('stop_words',)

    def get_queryset(self, request):
        qs = super(PromptAdmin, self).get_queryset(request)
        return qs.prefetch_related('stop_words')


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'active')


@admin.register(VacancyPromptDecision)
class VacancyPromptDecisionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'state', 'vacancy__title', 'prompt__title', 'notified', 'hh_url',
        'koef', 'consensus', 'vacancy__load_dt',
    )
    list_select_related = ('vacancy', 'prompt')
    exclude = ('llm_results',)
    list_filter = ('state', 'notified',)
    readonly_fields = ('vacancy', 'prompt', 'consensus', 'koef', 'notified', 'state', 'results', )

    def get_queryset(self, request):
        qs = super(VacancyPromptDecisionAdmin, self).get_queryset(request)
        return qs.prefetch_related('vacancy', 'prompt', 'llm_results')

    @admin.display(description='HH Url')
    def hh_url(self, obj):
        if obj.vacancy.url:
            return format_html('<a href="{}" target="_blank">Перейти</a>',  obj.vacancy.url)
        return ''

    def results(self, obj):
        result = ''
        for r in obj.llm_results.all():
            result += (f'<b>{r.get_llm_display()}: {r.corresponds}</b><br/><br/>'
                       f'<b>Comment</b>: {r.comment}<br/><br/>'
                       f'<b>Extra</b>: {r.extra}<br/><br/>'
                       f'======<br/><br/>')
        return mark_safe(result)


@admin.register(SearchQueryPromptLink)
class SearchQueryPromptLinkAdmin(admin.ModelAdmin):
    pass

@admin.register(ExecuteLLM)
class ExecuteLLMAdmin(admin.ModelAdmin):
    pass


@admin.register(LLMResult)
class LLMResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'llm', 'prompt', 'vacancy', 'task_hash')
    list_select_related = ('vacancy', 'prompt')


@admin.register(StopWord)
class StopWordAdmin(admin.ModelAdmin):
    search_fields = ('title',)
    ordering = ('title',)