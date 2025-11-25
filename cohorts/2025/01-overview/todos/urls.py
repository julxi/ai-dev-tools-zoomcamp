from django.urls import path
from . import views

app_name = "todos"

urlpatterns = [
    path("", views.TodoListView.as_view(), name="home"),
    path("create/", views.TodoCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", views.TodoUpdateView.as_view(), name="edit"),
    path("delete/<int:pk>/", views.TodoDeleteView.as_view(), name="delete"),
    path("toggle/<int:pk>/", views.toggle_resolved, name="toggle_resolved"),
]
