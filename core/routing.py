from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import modes.routing

application = ProtocolTypeRouter({
  "websocket": AuthMiddlewareStack(
        URLRouter(
            modes.routing.websocket_urlpatterns
        )
    ),
})