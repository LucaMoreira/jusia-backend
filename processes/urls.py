from django.urls import path
from . import views

urlpatterns = [
    # Busca de processos
    path('search/', views.search_process, name='search_process'),
    path('search/by-party/', views.search_by_party, name='search_by_party'),
    path('search/by-court/', views.search_by_court, name='search_by_court'),
    
    # Detalhes de processos
    path('details/<int:process_id>/', views.get_process_details, name='get_process_details'),
    
    # Histórico de buscas
    path('searches/', views.get_user_searches, name='get_user_searches'),
    
    # Favoritos
    path('favorites/', views.get_favorites, name='get_favorites'),
    path('favorites/<int:process_id>/add/', views.add_to_favorites, name='add_to_favorites'),
    path('favorites/<int:process_id>/remove/', views.remove_from_favorites, name='remove_from_favorites'),
    
    # Tribunais
    path('courts/', views.get_courts_list, name='get_courts_list'),
]



