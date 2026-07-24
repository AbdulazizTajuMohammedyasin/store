from celery import shared_task

from .services.collaborative import collaborative_filtering
from .services.content_based import content_based


@shared_task
def generate_recommendations():
    collaborative_filtering()
    content_based()