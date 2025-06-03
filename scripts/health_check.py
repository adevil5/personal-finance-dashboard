#!/usr/bin/env python
"""
Health check script for Personal Finance Dashboard services.
"""

import os
import sys

import psycopg  # noqa: F401
import redis

import django

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection  # noqa: E402


def check_postgresql():
    """Check PostgreSQL connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result[0] == 1:
                print("✅ PostgreSQL: Connected successfully")
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                print(f"   Version: {version.split(',')[0]}")
                return True
    except Exception as e:
        print(f"❌ PostgreSQL: Connection failed - {e}")
        return False


def check_redis():
    """Check Redis connection."""
    try:
        r = redis.Redis(
            host=settings.CACHES["default"]["LOCATION"].split("://")[1].split(":")[0],
            port=6379,
            db=1,
        )
        r.ping()
        print("✅ Redis: Connected successfully")
        info = r.info()
        print(f"   Version: {info['redis_version']}")
        return True
    except Exception as e:
        print(f"❌ Redis: Connection failed - {e}")
        return False


def check_django_cache():
    """Check Django cache configuration."""
    try:
        from django.core.cache import cache

        cache.set("health_check", "OK", 10)
        value = cache.get("health_check")
        if value == "OK":
            print("✅ Django Cache: Working correctly")
            return True
        else:
            print("❌ Django Cache: Not working properly")
            return False
    except Exception as e:
        print(f"❌ Django Cache: Error - {e}")
        return False


def check_celery():
    """Check Celery configuration."""
    try:
        from config.celery import app

        # Check if Celery app is configured
        print("✅ Celery: Configuration loaded")
        print(f"   Broker: {app.conf.broker_url}")
        print(f"   Backend: {app.conf.result_backend}")
        return True
    except Exception as e:
        print(f"❌ Celery: Configuration error - {e}")
        return False


def main():
    """Run all health checks."""
    print("Personal Finance Dashboard - Service Health Check")
    print("=" * 50)

    all_good = True

    # Check all services
    all_good &= check_postgresql()
    all_good &= check_redis()
    all_good &= check_django_cache()
    all_good &= check_celery()

    print("=" * 50)

    if all_good:
        print("✅ All services are healthy!")
        sys.exit(0)
    else:
        print("❌ Some services are not healthy. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
