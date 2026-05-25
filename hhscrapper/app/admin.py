from django.contrib import admin

from hhscrapper.app.models import Vacancy, LLMResult, Prompt, SearchQuery, VacancyPromptDecision, SearchQueryPromptLink, \
    ExecuteLLM, StopWord


# Register your models here.

class LLMResultInlineAdmin(admin.TabularInline):
    model = VacancyPromptDecision.llm_results.through


class SkillInlineAdmin(admin.TabularInline):
    model = Vacancy.skills.through


class StopWordInlineAdmin(admin.TabularInline):
    model = Prompt.stop_words.through


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    inlines = [SkillInlineAdmin]
    exclude = ('skills',)
    list_display = ('id', 'title', 'url', 'load_dt')


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    inlines = [StopWordInlineAdmin,]
    exclude = ('stop_words',)

@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    pass


@admin.register(VacancyPromptDecision)
class VacancyPromptDecisionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'state', 'vacancy__title', 'vacancy__url',
        'notified', 'koef', 'consensus', 'vacancy__load_dt'
    )
    list_select_related = ('vacancy',)

    inlines = [LLMResultInlineAdmin,]
    exclude = ('llm_results',)


@admin.register(SearchQueryPromptLink)
class SearchQueryPromptLinkAdmin(admin.ModelAdmin):
    pass

@admin.register(ExecuteLLM)
class ExecuteLLMAdmin(admin.ModelAdmin):
    pass


@admin.register(LLMResult)
class LLMResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'llm', 'prompt', 'vacancy')
    list_select_related = ('vacancy', 'prompt')


@admin.register(StopWord)
class StopWordAdmin(admin.ModelAdmin):
    pass