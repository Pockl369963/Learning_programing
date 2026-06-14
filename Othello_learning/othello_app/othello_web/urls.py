from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/move', views.api_move, name='api_move'),
    path('api/reset', views.api_reset, name='api_reset'),
    path('api/ai-move', views.api_ai_move, name='api_ai_move'),
    ]
