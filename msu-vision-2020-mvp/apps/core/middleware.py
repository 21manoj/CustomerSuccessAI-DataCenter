def ensure_user_profile_middleware(get_response):
    """Guarantee UserProfile exists for authenticated users (signal may miss edge cases)."""

    def middleware(request):
        if request.user.is_authenticated:
            from apps.stakeholders.models import UserProfile

            UserProfile.objects.get_or_create(user=request.user)
        return get_response(request)

    return middleware
