from django.urls import path

from collection.views import ServiceWorkerView, ManifestView, OfflineView

# The service worker cannot be in /static because its scope will be limited to /static.
urlpatterns = [
    path('sw.js', ServiceWorkerView.as_view(), name='serviceworker'),
    path('manifest.json', ManifestView.as_view(), name='manifest'),
    path('offline/', OfflineView.as_view(), name='offline'),
]