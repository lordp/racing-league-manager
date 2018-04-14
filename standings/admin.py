from django.contrib import admin
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from django.db.models import Max, F
from .models import *
import os
import contextlib

admin.site.site_header = 'FSR Admin'
admin.site.site_title = "FSR Admin"


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    @staticmethod
    def season(obj):
        return obj.race.season.name

    list_display = ('race', 'season', 'driver', 'team', 'position')
    list_select_related = ['race__season']
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
            'race_laps', 'race_time', 'gap', 'dnf_reason',
            'fastest_lap', 'race_fastest_lap'
        ]}),
        ('Race Penalties', {'fields': [
            'race_penalty_time', 'race_penalty_positions', 'race_penalty_description'
        ]}),
        ('Advanced', {'fields': ['subbed_by', 'allocate_points', 'note'], 'classes': ['collapse']}),
    ]


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_filter = ['season']
    list_display = ('name', 'season')
    list_select_related = ('season', 'season__division')
    ordering = ['name']
    actions = ['update_results', 'apply_penalties']

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

    def apply_penalties(self, request, queryset):
        if 'apply' in request.POST:
            race = Race.objects.get(pk=request.POST.get('_selected_action'))
            dsq = []
            max_pos = race.result_set.aggregate(Max('position'))['position__max']

            for result in race.result_set.all():
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

                result.save()

            for result in dsq:
                race.result_set.filter(position__gt=result.position).update(position=F('position') - 1)
                result.position = max_pos
                result.save()

            messages.add_message(request, messages.INFO, "Results for '{}' updated".format(race.name))
            return redirect(reverse("admin:standings_race_changelist"))
        else:
            race = queryset.first()
            results = race.result_set.all()
            context = dict(
                self.admin_site.each_context(request),
                race=race,
                results=results
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

    list_display = ('name', 'league', 'division')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'result_count', 'public_profile', 'country', 'shortname', 'city', 'birthday', 'helmet')
    search_fields = ['name']
    ordering = ['name']
    actions = ['move_results']

    def get_queryset(self, request):
        return Driver.objects.annotate(result_count=Count('result'))

    def result_count(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(
            "{}?{}".format(reverse('admin:standings_result_changelist'), 'driver__id__exact={}'.format(obj.id)),
            obj.result_count)
        )

    result_count.short_description = 'Results count'
    result_count.admin_order_field = 'result_count'

    def move_results(self, request, queryset):
        for obj in queryset:
            obj.collect_results()

        messages.add_message(request, messages.INFO, "Results for {} drivers moved".format(queryset.count()))
        return redirect(reverse("admin:standings_driver_changelist"))
    move_results.short_description = 'Merge driver results'

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
    list_filter = ['result__race', 'result__driver']
    ordering = ['lap_number']


@admin.register(LogFile)
class LogFileAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.process(request)

    def delete_model(self, request, obj):
        with contextlib.suppress(FileNotFoundError):
            os.remove(obj.file.path)

        super().delete_model(request, obj)


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('name', 'length', 'country', 'version')


admin.site.register([League, Division, Team, PointSystem])
