from rest_framework import serializers
from accounts.models import Address, CustomUser
from orders.models import Order, OrderItem
from products.models import Product
from products.serializers import ProductImageSerializer, ProductSerializer  # Assuming you have a serializer for Product model
from .models import Cart, CartItem


class ProductSerializer(serializers.ModelSerializer):
    # Add any additional fields related to the product
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = ['id', 'name', 'product_code', 'category_name', 'price_per_meter', 'offer', 'images','created_at','updated_at']


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = CartItem
        fields = [
            'id',
            'product',
            'quantity',
            'size',
            'sleeve',
            'price',
            'custom_length',
            'length',
            'offer_type',
            'discount_amount',
            'free_product'
        ]
        read_only_fields = ['id', 'price', 'discount_amount', 'free_product','created_at','updated_at']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id',
            'user',
            'items',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email', 'mobile_number',]
        read_only_fields= ['created_at', 'updated_at']

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id", "name", "email", "mobile_number", "address", "pincode",
            "landmark", "block", "district", "state", "country",
            "is_home", "is_office", "is_other", "is_default"
        ]
        read_only_fields= ['created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    free_product = ProductSerializer(required=False, allow_null=True)  # Handle free product as optional

    class Meta:
        model = OrderItem
        fields = [
            "product",
            "quantity",
            "size",
            "sleeve",
            "price",
            "custom_length",
            "length",
            "order",
            "free_product"  # Include free product in the response
        ]
        read_only_fields= ['created_at', 'updated_at']


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    shipping_address = AddressSerializer()
    items = OrderItemSerializer(many=True)  # Include multiple order items in the response


    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "shipping_address",
            "total_price",
            "status",
            "return_status",
            "payment_option",
            "payment_status",
            "items",
        ]
        read_only_fields= ['created_at', 'updated_at']
