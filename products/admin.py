from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from django.contrib.contenttypes.admin import GenericStackedInline
from .models import *
from tags.models import TaggedItem

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    search_fields = ['title']

class TagInline(GenericStackedInline):
    model = TaggedItem
    autocomplete_fields = ['tag']
    extra = 1

class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ['thumbnail']

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" />',
                obj.image.url
            )
        return "No image"

    thumbnail.short_description = "Preview"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['title']
    list_display = ['title','price']
    date_hierarchy = 'last_update' 
    list_editable = ['price']
    inlines = [TagInline, ImageInline]
    autocomplete_fields = ['collection']
    

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    search_fields = ['first_name']
    list_display =['first_name', 'last_name', 'membership','orders']
    list_select_related = ['user']
    list_editable = ['membership']
    ordering = ['user__first_name', 'user__last_name']
    @admin.display(ordering='orders_count', description='Orders')
    def orders(self, obj):
        url = (
            reverse("admin:products_order_changelist") 
            + f"?customer__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.orders_count)
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(orders_count= Count('order'))
    
    
class OrderItemAdd(admin.TabularInline):
    autocomplete_fields=['product']
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    autocomplete_fields = ['customer']
    inlines = [OrderItemAdd]
    list_display = ['id','placed_at','customer']
    list_select_related = ['customer']
    