import redis

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt


@never_cache
@csrf_exempt
def health_check(request):
    """Health check endpoint for monitoring."""
    health_status = {"status": "healthy", "checks": {}}

    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"

    # Check Redis connection
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = f"error: {str(e)}"

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JsonResponse(health_status, status=status_code)


def custom_404(request, exception):
    """Custom 404 error page."""
    return render(request, "errors/404.html", status=404)


def custom_500(request):
    """Custom 500 error page."""
    return render(request, "errors/500.html", status=500)


def ratelimit_exceeded(request, exception):
    """Rate limit exceeded view."""
    return render(request, "errors/ratelimit.html", status=429)
