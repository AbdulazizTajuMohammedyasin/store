from django.db import models
from products.models import Product, Customer

# Create your models here.

class ProductRecommendation(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="recommendations",
        on_delete=models.CASCADE
    )

    recommended_product = models.ForeignKey(
        Product,
        related_name="recommended_for",
        on_delete=models.CASCADE
    )

    score = models.FloatField()
    
class UserRecommendation(models.Model):

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    score = models.FloatField()