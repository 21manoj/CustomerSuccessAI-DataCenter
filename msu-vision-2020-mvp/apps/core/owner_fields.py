"""Shared widgets / querysets for accountability M2Ms (registered users only)."""

from django.contrib.auth import get_user_model


def active_registered_users_queryset():
    return get_user_model().objects.filter(is_active=True).order_by("username")


OWNERS_SELECT_ATTRS = {"class": "mt-1 block w-full rounded border p-2", "size": 10}
