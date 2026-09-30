from django.urls import path
from .views import CatalogView,PrepareAssessmentView,AssessmentView,AuthorizeAssessmentView,CancelAssessmentView,ChatMessageView,ChatTurnView,ConversationView
urlpatterns=[path('assistente/catalogo/',CatalogView.as_view(),name='catalog'),
path('assistente/mensagens/',ChatMessageView.as_view(),name='chat_message'),
path('assistente/mensagens/<uuid:turn_id>/',ChatTurnView.as_view(),name='chat_turn'),
path('assistente/conversas/<uuid:conversation_id>/',ConversationView.as_view(),name='conversation'),
path('projetos/<uuid:pk>/avaliar/',PrepareAssessmentView.as_view(),name='prepare_assessment'),
path('projetos/<uuid:pk>/avaliacoes/<uuid:run_id>/',AssessmentView.as_view(),name='assessment'),
path('projetos/<uuid:pk>/avaliacoes/<uuid:run_id>/autorizar/',AuthorizeAssessmentView.as_view(),name='authorize_assessment'),
path('projetos/<uuid:pk>/avaliacoes/<uuid:run_id>/cancelar/',CancelAssessmentView.as_view(),name='cancel_assessment')]
