from django import template

from app.models import SaleProduct

register = template.Library()


@register.simple_tag
def get_sale_products(sale: int):
    products = SaleProduct.objects.filter(sale=sale).order_by('pk')
    product_names = [str(p.product.name) for p in products]
    return product_names