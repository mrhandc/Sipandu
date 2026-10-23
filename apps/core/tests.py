from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import CustomUser


class CoreAdminUrlTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            username='core-admin',
            password='test-password-123',
            role=CustomUser.Role.ADMIN,
            status_akun=CustomUser.StatusAkun.AKTIF,
        )
        self.client.force_login(self.admin_user)

    def test_whatsapp_test_url_is_reachable(self):
        response = self.client.get(reverse('core:whatsapp_test'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/whatsapp_test.html')

    def test_audit_log_url_is_reachable(self):
        response = self.client.get(reverse('core:audit_log_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/audit_log_list.html')

    def test_django_admin_remains_reachable(self):
        response = self.client.get('/admin/', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/login.html')

# Create your tests here.
