from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/mode/(?P<serial_number>\w+)/$', consumers.ModeConsumer, {'has_ticket': False}),
    re_path(r'ws/mode/(?P<serial_number>\w+)/(?P<ticket>\w+)/$', consumers.ModeConsumer, {'has_ticket': True}),
]