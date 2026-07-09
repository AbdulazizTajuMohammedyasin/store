from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings
from .models import Customer, Cart

@receiver(post_save, sender= settings.AUTH_USER_MODEL)
def create_customer(sender, instance, created, **kwargs):
    if created:
        Customer.objects.create(user=instance)
        
@receiver(post_save, sender=Customer)
def create_cart(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(customer=instance)