from django.urls import path
from .views import MapView,SourceView,InspectView,AnalysisView,RevokeConnectorView
from .api import ConnectorAPI
urlpatterns=[path('projetos/<uuid:pk>/mapa/',MapView.as_view(),name='map'),path('projetos/<uuid:pk>/analise/',AnalysisView.as_view(),name='analysis'),
    path('api/conector/',ConnectorAPI.as_view(),name='connector_api'),
    path('projetos/<uuid:pk>/conectores/<uuid:connector_id>/revogar/',RevokeConnectorView.as_view(),name='revoke_connector'),
    path('projetos/<uuid:pk>/snapshots/<uuid:snapshot_id>/fontes/<str:source_id>/',SourceView.as_view(),name='source'),
    path('projetos/<uuid:pk>/snapshots/<uuid:snapshot_id>/elementos/<str:node_id>/',InspectView.as_view(),name='inspect_node')]
