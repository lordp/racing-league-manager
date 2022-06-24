from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from standings_api import views

urlpatterns = [
    url(r'^drivers$', views.DriverList.as_view()),
    url(r'^teams$', views.TeamList.as_view()),
    url(r'^results$', views.ResultList.as_view()),
    url(r'^drivers/(?P<number>[0-9]+)/(?P<season_id>[0-9]+)$', views.DriverDetail.as_view()),
    url(r'^teams/(?P<pk>[0-9]+)$', views.TeamDetail.as_view()),
    url(r'^races$', views.RaceList.as_view()),
    url(r'^races/(?P<race_id>[0-9]+)$', views.RaceDetail.as_view()),
    url(r'^next-race$', views.NextRaceDetail.as_view()),
    url(r'^stats$', views.DriverStats.as_view()),
    url(r'^standings/(?P<season_id>[0-9]+)(/(?P<team>team))?$', views.Standings.as_view()),
    url(r'^info/(?P<division_name>[A-Za-z ]+)$', views.DivisionInfo.as_view()),
    url(r'^season/(?P<season_id>[0-9]+)$', views.SeasonDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
