from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils.translation import gettext_lazy as _


class AdminPermission(PermissionRequiredMixin):
    """Verify that the current user is a staff member."""
    permission_denied_message = _("You don't have permission to access this page.")
    login_url = '/login/'

    def has_permission(self):
        return True if self.request.user.is_staff else False
