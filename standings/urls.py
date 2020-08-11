from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('season/<int:season_id>/', views.season_view, name='season'),
    path('season/<int:season_id>/stats', views.season_stats_view, name='season_stats'),
    path('team/<int:team_id>/', views.team_view, name='team'),
    path('team/<str:slug>/', views.team_view_slug, name='team_slug'),
    path('driver/<int:driver_id>/', views.driver_view, name='driver'),
    path('driver/<str:slug>/', views.driver_view_slug, name='driver_slug'),
    path('league/<int:league_id>/', views.league_view, name='league'),
    path('division/<int:division_id>/', views.division_view, name='division'),
    path('race/<int:race_id>/', views.race_view, name='race'),
    path('track/<int:track_id>/', views.track_view, name='track'),
    path('laps/<int:result_id>', views.laps_view, name='laps'),
    re_path(r'^countries/(?:(?P<division>\d+)/)?$', views.countries_view, name='countries'),
    re_path(r'^country/(?P<country_id>[A-Z]+)/(?:(?P<division>\d+)/)?$', views.country_view, name='country'),
    path('<slug:division>/<slug:season>', views.season_view_alternate, name='season_alternate'),
]
