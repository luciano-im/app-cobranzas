from django.views.generic import TemplateView


class ServiceWorkerView(TemplateView):
    template_name = 'sw.js'
    content_type = 'application/javascript'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['version'] = '0.1'
        return context


class ManifestView(TemplateView):
    template_name = 'manifest.json'
    content_type = 'application/json'


class OfflineView(TemplateView):
    template_name = 'offline.html'