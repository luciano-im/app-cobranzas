from rest_framework import serializers
from app.models import Sale, Customer, SaleInstallment

# Terminology for serializers
# SBC = Sales By Customer

# SALES BY CUSTOMER

# class SBYSaleProductSerializer(serializers.ModelSerializer):
#     product = serializers.CharField(source='product.name')

#     class Meta:
#         model = SaleProduct
#         fields = ['product']


class SBCSaleInstallmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleInstallment
        fields = ['pk', 'installment', 'installment_amount', 'paid_amount', 'status']


class SBCSaleSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    saleinstallment_set = SBCSaleInstallmentsSerializer(read_only=True, many=True)

    class Meta:
        model = Sale
        fields = ['pk', 'price', 'installments', 'date', 'remarks', 'products', 'paid_amount', 'pending_balance', 'saleinstallment_set']

    def get_products(self, obj):
        return obj.saleproduct_set.all().values_list("product__name", flat=True)


class SalesByCustomerSerializer(serializers.ModelSerializer):
    sale_set = SBCSaleSerializer(read_only=True, many=True)

    class Meta:
        model = Customer
        fields = ['pk', 'sale_set']




# CUSTOMER

class CustomersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['pk', 'name', 'address', 'telephone', 'city']
