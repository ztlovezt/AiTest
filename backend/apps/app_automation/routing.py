from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/app-automation/executions/(?P<execution_id>\d+)/$', consumers.AppExecutionConsumer.as_asgi()),
    re_path(r'^ws/app-automation/remote-device/(?P<device_id>[^/]+)/$', consumers.RemoteDeviceConsumer.as_asgi()),
]
