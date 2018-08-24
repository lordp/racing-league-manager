from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import helpers
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from django.db.models import Max, F
from .models import *
import os
import contextlib
from .utils import format_time, expire_view_cache

admin.site.site_header = 'FSR Admin'
admin.site.site_title = "FSR Admin"


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        expire_view_cache(
            reverse('season', args=[obj.race.season.id]),
            meta=request.META
        )
        SeasonStats.objects.get(season=obj.race.season, driver=obj.driver).update_stats()

    @staticmethod
    def season(obj):
        return obj.race.season.name

    list_display = ('race', 'season', 'driver', 'team', 'position')
    list_select_related = ['race', 'race__season', 'race__season__division', 'race__season__division__league']
    list_filter = (
        ('race__season__division__league', RelatedDropdownFilter),
        ('race__season__division', RelatedDropdownFilter),
        ('race__season', RelatedDropdownFilter),
        ('race', RelatedDropdownFilter),
        ('driver', RelatedDropdownFilter),
    )
    search_fields = ['driver__name']

    fieldsets = [
        (None, {'fields': [
            'race', 'driver', 'team', 'finalized', 'car', 'car_class',
            'points', 'points_multiplier', 'points_multiplier_description',
        ]}),
        ('Qualifying', {'fields': ['qualifying', 'qualifying_laps', 'qualifying_time']}),
        ('Qualifying Penalties', {'fields': [
            'qualifying_penalty_grid', 'qualifying_penalty_bog',
            'qualifying_penalty_sfp', 'qualifying_penalty_description', 'qualifying_fastest_lap'
        ]}),
        ('Race', {'fields': [
            'position', 'race_laps', 'race_time', 'gap', 'dnf_reason',
            'fastest_lap', 'race_fastest_lap'
        ]}),
        ('Race Penalties', {'fields': [
            'race_penalty_time', 'race_penalty_positions', 'race_penalty_description'
        ]}),
        ('Advanced', {'fields': ['subbed_by', 'allocate_points', 'note'], 'classes': ['collapse']}),
    ]


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_filter = [('season', RelatedDropdownFilter)]
    list_display = ('name', 'round_number', 'start_time', 'season')
    list_select_related = ('season', 'season__division')
    ordering = ['start_time', 'round_number']
    actions = ['update_results', 'apply_penalties', 'unfinalise']

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('apply_penalties/', self.apply_penalties),
        ]
        return my_urls + urls

    def update_results(self, request, queryset):
        for obj in queryset:
            obj.fill_attributes()

        messages.add_message(request, messages.INFO, "{} race(s) updated".format(queryset.count()))
        return redirect(reverse("admin:standings_race_changelist"))
    update_results.short_description = 'Update result information (points, gaps, etc)'

    def unfinalise(self, request, queryset):
        for obj in queryset:
            Result.objects.filter(race=obj).update(finalized=False)

        messages.add_message(request, messages.INFO, "{} race(s) unfinalised".format(queryset.count()))
        return redirect(
            "{}?season__id__exact={}".format(
                reverse("admin:standings_race_changelist"),
                request.GET.get('season__id__exact', None)
            )
        )
    unfinalise.short_description = 'Set all results for a race to be unfinalised'

    def apply_penalties(self, request, queryset):
        if 'apply' in request.POST:
            race = Race.objects.get(pk=request.POST.get('_selected_action'))
            dsq = []
            pens = set()
            max_pos = race.result_set.aggregate(Max('position'))['position__max']

            for result in race.result_set.filter(finalized=False):
                result.position = request.POST.get('position-{}'.format(result.id))
                result.race_time = request.POST.get('race-time-{}'.format(result.id))
                result.race_penalty_time = request.POST.get('pen-time-{}'.format(result.id), 0)
                result.race_penalty_positions = request.POST.get('pen-pos-{}'.format(result.id), 0)
                result.race_penalty_description = request.POST.get('pen-desc-{}'.format(result.id), '')
                result.qualifying_penalty_bog = True if 'qpen-bog-{}'.format(result.id) in request.POST else False
                result.qualifying_penalty_sfp = True if 'qpen-sfp-{}'.format(result.id) in request.POST else False
                result.qualifying_penalty_dsq = True if 'qpen-dsq-{}'.format(result.id) in request.POST else False
                result.qualifying_penalty_grid = request.POST.get('qpen-grid-{}'.format(result.id), 0)
                result.qualifying_penalty_description = request.POST.get('qpen-desc-{}'.format(result.id), '')
                result.penalty_points = request.POST.get('pen-pts-{}'.format(result.id), 0)

                if 'pen-dsq-{}'.format(result.id) in request.POST:
                    result.race_penalty_dsq = True
                    dsq.append(result)
                else:
                    result.race_penalty_dsq = False

                if int(request.POST.get('pen-time-{}'.format(result.id), 0)) > 0:
                    result.race_time = float(result.race_time) + float(result.race_penalty_time)
                    pens.add(result.race_laps)

                result.finalized = True
                result.save()

            for result in dsq:
                result.refresh_from_db()
                race.result_set.filter(position__gt=result.position).update(position=F('position') - 1)
                result.position = max_pos
                result.save()

            for result_laps in pens:
                results = race.result_set.filter(race_laps=result_laps, race_penalty_dsq=False).order_by('race_time')
                highest_position = results.aggregate(Min('position'))['position__min']
                for index, result in enumerate(results):
                    result.position = highest_position + index
                    result.save()

            if dsq or pens:
                race.fill_attributes()

            if request.POST['clear-cache']:
                expire_view_cache(
                    reverse('season', args=[race.season_id]),
                    meta=request.META
                )

            messages.add_message(request, messages.INFO, "Results for '{}' updated".format(race.name))
            return redirect(
                "{}?season__id__exact={}".format(
                    reverse("admin:standings_race_changelist"),
                    request.GET.get('season__id__exact', None)
                )
            )
        else:
            race = queryset.first()
            results = race.result_set.all()
            context = dict(
                self.admin_site.each_context(request),
                race=race,
                results=results,
                title="Apply penalties"
            )
            return TemplateResponse(request, "admin/apply_penalties.html", context)
    apply_penalties.short_description = 'Apply penalties and adjust time/positions'


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    @staticmethod
    def league(obj):
        return obj.division.league.name

    @staticmethod
    def division(obj):
        return obj.division.name

    list_display = ('name', 'league', 'division', 'race_count')
    list_filter = ('division', 'division__league')
    actions = ['generate_top10', 'update_stats', 'clear_cache']
    ordering = ['start_date']

    def get_queryset(self, request):
        return Season.objects.annotate(race_count=Count('race'))

    @staticmethod
    def race_count(obj):
        return obj.race_count

    def generate_top10(self, request, queryset):
        for obj in queryset:
            obj.generate_top10()

        messages.add_message(request, messages.INFO, "Top 10 images generated")
        return redirect(reverse("admin:standings_season_changelist"))
    generate_top10.short_description = 'Generate top 10 images'

    def update_stats(self, request, queryset):
        for obj in queryset:
            obj.update_stats()

        messages.add_message(request, messages.INFO, "Season stats updated")
        return redirect(reverse("admin:standings_season_changelist"))
    update_stats.short_description = 'Update season based stats'

    def clear_cache(self, request, queryset):
        for obj in queryset:
            expire_view_cache(
                reverse('season', args=[obj.id]),
                meta=request.META
            )

        messages.add_message(request, messages.INFO, "Cache cleared for selected seasons")
        return redirect(reverse("admin:standings_season_changelist"))
    clear_cache.short_description = 'Clear cache'


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'result_count', 'public_profile', 'country', 'shortname', 'city', 'birthday', 'helmet')
    search_fields = ['name']
    ordering = ['name']
    actions = ['merge_results']

    def get_queryset(self, request):
        return Driver.objects.annotate(result_count=Count('result'))

    def result_count(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(
            "{}?{}".format(reverse('admin:standings_result_changelist'), 'driver__id__exact={}'.format(obj.id)),
            obj.result_count)
        )

    result_count.short_description = 'Results count'
    result_count.admin_order_field = 'result_count'

    def merge_results(self, request, queryset):
        if 'apply' in request.POST:
            chosen_driver = request.POST.get('chosen_driver', None)
            if chosen_driver:
                chosen_driver = Driver.objects.get(pk=chosen_driver)
                chosen_driver.collect_results(queryset)
                if request.POST.get('delete_others', None):
                    for driver in queryset.exclude(id=chosen_driver.id).all():
                        driver.delete()

                messages.add_message(request, messages.INFO, "Results moved to '{}'".format(chosen_driver.name))
            else:
                messages.add_message(request, messages.WARNING, "No driver was chosen")

            return redirect(reverse("admin:standings_driver_changelist"))
        else:
            context = {
                **self.admin_site.each_context(request),
                'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
                'drivers': queryset,
                'driver_ids': map(str, queryset.values_list('id', flat=True)),
                'title': "Merge results",
            }
            return TemplateResponse(request, "admin/merge_results.html", context)
    merge_results.short_description = 'Merge driver results'

    @staticmethod
    def public_profile(obj):
        return mark_safe('<a href="{}">{}</a>'.format(reverse('driver', args=(obj.id,)), obj.name))

    class Media:
        css = {
            "all": ("admin/css/standings.css",)
        }


@admin.register(Lap)
class LapAdmin(admin.ModelAdmin):
    list_display = ('result', 'lap_number', 'position', 'sector_1', 'sector_2', 'sector_3', 'lap_time', 'pitstop')
    list_filter = [('result__race', RelatedDropdownFilter), ('result__driver', RelatedDropdownFilter), 'session']
    ordering = ['lap_number']


@admin.register(LogFile)
class LogFileAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.process()

    def delete_model(self, request, obj):
        with contextlib.suppress(FileNotFoundError):
            os.remove(obj.file.path)

        super().delete_model(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        return redirect(reverse("admin:standings_logfile_summary", args=(obj.id,)))

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('<int:logfile_id>/summary', self.summary, name='standings_logfile_summary'),
        ]
        return my_urls + urls

    def summary(self, request, logfile_id):
        log_file = LogFile.objects.get(pk=logfile_id)
        summary = json.loads(log_file.summary)
        duplicates = []
        lap_errors = []

        for driver_id in summary['duplicates']:
            driver = Driver.objects.get(pk=driver_id)
            duplicates.append({'id': driver.id, 'name': driver.name})

        for driver_id in summary['lap_errors']:
            driver = Driver.objects.get(pk=driver_id)
            lap_errors.append({
                'driver': {'id': driver.id, 'name': driver.name},
                'laps': summary['lap_errors'][driver_id]
            })

        context = dict(
            self.admin_site.each_context(request),
            log_file=log_file,
            duplicates=duplicates,
            lap_errors=lap_errors,
            title="Log file summary"
        )
        return TemplateResponse(request, "admin/summary.html", context)


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('name', 'length', 'country', 'version', 'race_count')
    actions = ['update_records']

    def update_records(self, request, queryset):
        for obj in queryset:
            obj.update_records()

        messages.add_message(request, messages.INFO, "Records for {} tracks updated".format(queryset.count()))
        return redirect(reverse("admin:standings_track_changelist"))
    update_records.short_description = 'Update track records'

    def get_queryset(self, request):
        return Track.objects.annotate(race_count=Count('race'))

    @staticmethod
    def race_count(obj):
        return obj.race_count


@admin.register(SeasonPenalty)
class SeasonPenaltyAdmin(admin.ModelAdmin):
    list_display = ('season', 'driver', 'team', 'points', 'disqualified')
    list_select_related = ('season', 'driver', 'team')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.process()


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'result_count', 'country', 'parent')
    ordering = ('name',)
    actions = ['merge_results']

    def get_queryset(self, request):
        return Team.objects.annotate(result_count=Count('result'))

    def result_count(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(
            "{}?{}".format(reverse('admin:standings_result_changelist'), 'team__id__exact={}'.format(obj.id)),
            obj.result_count)
        )

    result_count.short_description = 'Results count'
    result_count.admin_order_field = 'result_count'

    def merge_results(self, request, queryset):
        if 'apply' in request.POST:
            chosen_team = request.POST.get('chosen_team', None)
            if chosen_team:
                chosen_team = Team.objects.get(pk=chosen_team)
                chosen_team.collect_results(queryset)
                if request.POST.get('delete_others', None):
                    for team in queryset.exclude(id=chosen_team.id).all():
                        team.delete()

                messages.add_message(request, messages.INFO, "Results moved to '{}'".format(chosen_team.name))
            else:
                messages.add_message(request, messages.WARNING, "No team was chosen")

            return redirect(reverse("admin:standings_team_changelist"))
        else:
            context = {
                **self.admin_site.each_context(request),
                'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
                'teams': queryset,
                'team_ids': map(str, queryset.values_list('id', flat=True)),
                'title': "Merge results",
            }
            return TemplateResponse(request, "admin/merge_team_results.html", context)
    merge_results.short_description = 'Merge team results'


@admin.register(SeasonStats)
class SeasonStatsAdmin(admin.ModelAdmin):
    list_filter = (
        ('season', RelatedDropdownFilter),
        ('driver', RelatedDropdownFilter),
    )

    list_select_related = ['season', 'driver']
    list_display = ['season', 'driver', 'best_result', 'wins', 'podiums', 'points_finishes',
                    'pole_positions', 'fastest_laps', 'laps_lead', 'laps_completed', 'winner',
                    'penalty_points', 'race_penalty_time', 'race_penalty_positions', 'qualifying_penalty_grid',
                    'qualifying_penalty_bog', 'qualifying_penalty_sfp', 'race_penalty_dsq', 'qualifying_penalty_dsq',
                    ]
    actions = ['update_stats']

    def update_stats(self, request, queryset):
        for obj in queryset:
            obj.update_stats()

        messages.add_message(request, messages.INFO, "Stats for {} drivers updated".format(queryset.count()))
        return redirect(reverse("admin:standings_seasonstats_changelist"))
    update_stats.short_description = 'Update season stats'


@admin.register(TrackRecord)
class TrackRecordAdmin(admin.ModelAdmin):
    list_select_related = ['track', 'driver', 'race', 'season']
    list_display = ['track', 'driver', 'race', 'season', 'session_type', 'formatted_lap_time']

    def formatted_lap_time(self, obj):
        return format_time(obj.lap_time)

    formatted_lap_time.short_description = 'Lap Time'
    formatted_lap_time.admin_order_field = 'formatted_lap_time'


admin.site.register([League, Division, PointSystem])
