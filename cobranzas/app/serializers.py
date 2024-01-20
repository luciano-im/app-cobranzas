from rest_framework import serializers
from rest_framework.renderers import BaseRenderer
from app.models import Sale, Customer, SaleProduct, SaleInstallment

# Terminology for serializers
# SBC = Sales By Customer
# IBC = Installments By Customer

# SALES BY CUSTOMER

# class SBYSaleProductSerializer(serializers.ModelSerializer):
#     product = serializers.CharField(source='product.name')

#     class Meta:
#         model = SaleProduct
#         fields = ['product']


class SBCSaleSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['pk', 'price', 'installments', 'date', 'remarks', 'products', 'paid_amount', 'pending_balance']

    def get_products(self, obj):
        return obj.saleproduct_set.all().values_list("product__name", flat=True)


class SalesByCustomerSerializer(serializers.ModelSerializer):
    sale_set = SBCSaleSerializer(read_only=True, many=True)

    class Meta:
        model = Customer
        fields = ['pk', 'sale_set']


# INSTALLMENTS BY CUSTOMER

class IBCSaleInstallmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleInstallment
        fields = ['pk', 'installment', 'installment_amount', 'paid_amount', 'status']


class IBCSaleSerializer(serializers.ModelSerializer):
    saleinstallment_set = IBCSaleInstallmentsSerializer(read_only=True, many=True)

    class Meta:
        model = Sale
        fields = ['pk', 'saleinstallment_set']


class InstallmentsByCustomerSerializer(serializers.ModelSerializer):
    sale_set = IBCSaleSerializer(read_only=True, many=True)

    class Meta:
        model = Customer
        fields = ['pk', 'sale_set']


# CUSTOMER

class CustomersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['pk', 'name', 'address', 'telephone', 'city']


# RENDEDERER

class JsonISO88591EncodingRenderer(BaseRenderer):
    media_type = 'application/json'
    format = 'json'
    charset = 'iso-8859-1'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data.encode(self.charset)