from django.core.management import call_command
from django.test import TestCase

from apps.events.models import Event
from apps.needs.models import Need
from apps.projects.models import Project


class SeedWorkflowTests(TestCase):
    def test_load_demo_data_creates_hostel_workflow(self):
        call_command("load_demo_data")
        self.assertTrue(Need.objects.filter(title__icontains="Boys Hostel").exists())
        self.assertTrue(Project.objects.filter(title__icontains="Boys Hostel").exists())
        self.assertTrue(Event.objects.filter(title__icontains="July 2026").exists())
