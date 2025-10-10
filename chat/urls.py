from django.urls import path
from . import views

urlpatterns = [
    # Sessões de chat
    path('sessions/', views.get_chat_sessions, name='get_chat_sessions'),
    path('sessions/create/', views.create_chat_session, name='create_chat_session'),
    path('sessions/<int:session_id>/', views.get_chat_session, name='get_chat_session'),
    path('sessions/<int:session_id>/delete/', views.delete_chat_session, name='delete_chat_session'),
    
    # Mensagens
    path('sessions/<int:session_id>/send/', views.send_message, name='send_message'),
    
    # Análise de processos
    path('analyze/process/<int:process_id>/', views.analyze_process, name='analyze_process'),
]




