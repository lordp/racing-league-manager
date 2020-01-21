from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter


class RLMFilter(RelatedDropdownFilter):
    template = 'admin/rlm_filter.html'

    def field_choices(self, field, request, model_admin):
        choice_limits = {
            'league': {
                'race__id__exact': 'division__season__race__id',
                'race__season__division__id__exact': 'division__id',
                'race__season__id__exact': 'division__season__id',
                'driver__id__exact': 'division__season__race__result__driver__id'
            },
            'division': {
                'race__season__division__league__id__exact': 'league__id',
                'race__id__exact': 'season__race__id',
                'race__season__id__exact': 'season__id',
                'driver__id__exact': 'season__race__result__driver__id'
            },
            'season': {
                'race__season__division__league__id__exact': 'division__league__id',
                'race__id__exact': 'race__id',
                'race__season__division__id__exact': 'division__id',
                'driver__id__exact': 'race__result__driver__id'
            },
            'race': {
                'race__season__division__league__id__exact': 'season__division__league__id',
                'race__season__division__id__exact': 'season__division__id',
                'race__season__id__exact': 'season__id',
                'driver__id__exact': 'result__driver__id'
            },
            'driver': {
                'race__season__division__league__id__exact': 'result__race__season__division__league__id',
                'race__id__exact': 'result__race__id',
                'race__season__division__id__exact': 'result__race__season__division__id',
                'race__season__id__exact': 'result__race__season__id',
            }
        }

        limit_choices_to = {}

        for filter_name, field_name in choice_limits[field.name].items():
            if filter_name in request.GET:
                limit_choices_to[field_name] = int(request.GET.get(filter_name))

        return self.unique(field.get_choices(include_blank=False, limit_choices_to=limit_choices_to))

    def has_output(self):
        return True

    def unique(self, choices):
        seen = set()
        seen_add = seen.add
        return [x for x in choices if not (x in seen or seen_add(x))]
