from django.contrib import admin

from hhscrapper.app.models import Vacancy, LLMResult


# Register your models here.

class LLMResultInlineAdmin(admin.TabularInline):
    model = LLMResult


class SkillInlineAdmin(admin.TabularInline):
    model = Vacancy.skills.through


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    inlines = [LLMResultInlineAdmin, SkillInlineAdmin]
    exclude = ('skills',)
    list_display = ('id', 'title', 'notified', 'koef', 'consensus', 'load_dt')
