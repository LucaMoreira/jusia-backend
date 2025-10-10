"""
Health check views for Google Cloud Run
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def health_live(request):
    """
    Liveness probe - checks if the application is running
    This should be lightweight and not depend on external services
    """
    try:
        return JsonResponse({
            'status': 'healthy',
            'service': 'jusia-backend',
            'check': 'liveness'
        }, status=200)
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JsonResponse({
            'status': 'unhealthy',
            'service': 'jusia-backend',
            'check': 'liveness',
            'error': str(e)
        }, status=503)


def health_ready(request):
    """
    Readiness probe - checks if the application is ready to serve traffic
    This checks database connectivity and other critical dependencies
    """
    try:
        # Check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Check cache connectivity (if using Redis/Memcached)
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        
        return JsonResponse({
            'status': 'ready',
            'service': 'jusia-backend',
            'check': 'readiness',
            'database': 'connected',
            'cache': 'connected'
        }, status=200)
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JsonResponse({
            'status': 'not_ready',
            'service': 'jusia-backend',
            'check': 'readiness',
            'error': str(e)
        }, status=503)
