from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from .models import Todo

User = get_user_model()


# Helper factory
def make_todo(title="Task", days_offset=None, resolved=False, description="desc"):
    due = None
    if days_offset is not None:
        due = date.today() + timedelta(days=days_offset)
    return Todo.objects.create(
        title=title, description=description, due_date=due, resolved=resolved
    )


# -------------------------
# Model tests
# -------------------------
class TodoModelTest(TestCase):
    def test_default_resolved_is_false_and_str(self):
        t = make_todo("My Task")
        self.assertFalse(t.resolved)
        self.assertEqual(str(t), "My Task")

    def test_ordering_newest_first(self):
        # Create two objects and ensure ordering by created_at descending
        older = make_todo("older")
        newer = make_todo("newer")
        qs = list(Todo.objects.all())
        self.assertEqual(qs[0].title, "newer")


# -------------------------
# Views & forms tests
# -------------------------
class TodoViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_shows_created_todo(self):
        make_todo("Buy milk")
        resp = self.client.get(reverse("todos:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Buy milk")

    def test_create_view_creates_and_redirects(self):
        resp = self.client.post(
            reverse("todos:create"),
            {
                "title": "New item",
                "description": "some desc",
                "due_date": (date.today() + timedelta(days=3)).isoformat(),
                "resolved": False,
            },
        )
        self.assertIn(resp.status_code, (302, 303))
        self.assertTrue(Todo.objects.filter(title="New item").exists())

    def test_create_view_rejects_missing_title(self):
        resp = self.client.post(
            reverse("todos:create"),
            {
                "title": "",
                "description": "no title",
                "due_date": "",
                "resolved": False,
            },
        )
        # form should re-render with errors (status 200) and not create
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Todo.objects.filter(description="no title").exists())
        # Default Django error text; change if you customized messages
        self.assertContains(resp, "This field is required")

    def test_create_view_rejects_bad_date_format(self):
        resp = self.client.post(
            reverse("todos:create"),
            {
                "title": "Bad date",
                "due_date": "not-a-date",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Todo.objects.filter(title="Bad date").exists())
        self.assertContains(resp, "Enter a valid date")

    def test_edit_view_updates_fields(self):
        t = make_todo("Old title")
        resp = self.client.post(
            reverse("todos:edit", args=[t.pk]),
            {
                "title": "Brand new",
                "description": "updated",
                "due_date": "",
                "resolved": True,
            },
        )
        self.assertIn(resp.status_code, (302, 303))
        t.refresh_from_db()
        self.assertEqual(t.title, "Brand new")
        self.assertTrue(t.resolved)

    def test_delete_view_removes_object(self):
        t = make_todo("To be deleted")
        resp = self.client.post(reverse("todos:delete", args=[t.pk]))
        self.assertIn(resp.status_code, (302, 303))
        self.assertFalse(Todo.objects.filter(pk=t.pk).exists())


# -------------------------
# Toggle + concurrency tests
# -------------------------
class ToggleAndConcurrencyTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_toggle_resolved_toggles_and_double_toggle(self):
        t = make_todo("Toggle me", resolved=False)
        resp1 = self.client.get(reverse("todos:toggle_resolved", args=[t.pk]))
        self.assertIn(resp1.status_code, (302, 303))
        t.refresh_from_db()
        self.assertTrue(t.resolved)

        resp2 = self.client.get(reverse("todos:toggle_resolved", args=[t.pk]))
        self.assertIn(resp2.status_code, (302, 303))
        t.refresh_from_db()
        self.assertFalse(t.resolved)

    def test_sequential_updates_simulate_race(self):
        t = make_todo("Race", resolved=False)
        copy1 = Todo.objects.get(pk=t.pk)
        copy2 = Todo.objects.get(pk=t.pk)

        copy1.resolved = True
        copy1.save()

        copy2.description = "worker2 update"
        copy2.save()

        t.refresh_from_db()
        self.assertTrue(t.resolved)
        self.assertEqual(t.description, "worker2 update")


# -------------------------
# Admin integration tests
# -------------------------
class AdminIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.login(username="admin", password="pass")

    def test_admin_changelist_shows_model(self):
        make_todo("Admin visible")
        url = reverse("admin:todos_todo_changelist")  # admin:<app>_<model>_changelist
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Admin visible")


# -------------------------
# List & pagination / business logic tests
# -------------------------
class ListAndPaginationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_many_todos_shown(self):
        for i in range(15):
            make_todo(f"Item {i}")
        resp = self.client.get(reverse("todos:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Item 0")


class DueDateBusinessLogicTests(TestCase):
    def test_past_due_marker(self):
        past = make_todo("past", days_offset=-2)
        future = make_todo("future", days_offset=5)
        resp = self.client.get(reverse("todos:home"))
        self.assertContains(resp, "past")
        self.assertContains(resp, "future")
        # If you later add a template marker for past-due items, extend this test
