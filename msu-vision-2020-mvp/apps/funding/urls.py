from django.urls import path

from apps.funding import views

app_name = "funding"

urlpatterns = [
    path("pools/", views.FundPoolListView.as_view(), name="pools"),
    path("contributions/", views.ContributionListView.as_view(), name="contributions"),
    path("contributions/create/", views.ContributionCreateView.as_view(), name="contribution_create"),
    path("expenses/", views.ExpenseListView.as_view(), name="expenses"),
    path("expenses/create/", views.ExpenseCreateView.as_view(), name="expense_create"),
    path("expenses/<int:pk>/approve/", views.expense_approve, name="expense_approve"),
    path("expenses/<int:pk>/disburse/", views.expense_disburse, name="expense_disburse"),
]
