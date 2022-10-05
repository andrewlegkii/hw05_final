from django.contrib import admin
from django.urls import include, path

from django.conf import settings
from django.conf.urls.static import static

from yatube.settings import MEDIA_URL
from yatube.settings import MEDIA_ROOT


handler403 = 'core.views.permission_denied'
handler404 = 'core.views.page_not_found'
handler500 = 'core.views.server_error'

urlpatterns = [
    path('auth/', include('users.urls', namespace='users')),
    path('auth/', include('django.contrib.auth.urls')),
    path('', include('posts.urls', namespace='posts')),
    path('admin/', admin.site.urls),
    path('about/', include('about.urls', namespace='about')),
]

if settings.DEBUG:
    urlpatterns += static(
        MEDIA_URL, document_root=MEDIA_ROOT
    )
