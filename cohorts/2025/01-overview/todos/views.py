from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Case, When, Value, BooleanField
from .models import Todo
from .forms import TodoForm


class TodoListView(ListView):
    model = Todo
    template_name = "todos/home.html"
    context_object_name = "todos"


class TodoCreateView(CreateView):
    model = Todo
    form_class = TodoForm
    template_name = "todos/todo_form.html"
    success_url = reverse_lazy("todos:home")


class TodoUpdateView(UpdateView):
    model = Todo
    form_class = TodoForm
    template_name = "todos/todo_form.html"
    success_url = reverse_lazy("todos:home")

    def form_valid(self, form):
        """
        Only save the fields that actually changed in the form. This prevents
        overwriting concurrent updates to unrelated fields (avoids lost-update).
        """
        obj = form.save(commit=False)
        changed = list(form.changed_data)
        if changed:
            # include updated_at if using an auto-updated timestamp and you want it refreshed
            if "updated_at" not in changed:
                changed.append("updated_at")
            obj.save(update_fields=changed)
        # If no fields changed, do not perform any save.
        return redirect(self.get_success_url())


class TodoDeleteView(DeleteView):
    model = Todo
    template_name = "todos/todo_confirm_delete.html"
    success_url = reverse_lazy("todos:home")


def toggle_resolved(request, pk):
    """
    Perform an atomic toggle of the boolean 'resolved' field in a single DB
    statement to avoid race conditions when multiple workers toggle concurrently.
    """
    Todo.objects.filter(pk=pk).update(
        resolved=Case(
            When(resolved=True, then=Value(False)),
            default=Value(True),
            output_field=BooleanField(),
        )
    )
    return redirect("todos:home")
