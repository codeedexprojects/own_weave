from rest_framework import serializers
from accounts.models import CustomUser
from accounts.serializers import AddressSerializer
from products.models import Product
from .models import AdminOrderProduct, Order, OrderItem,AdminOrder
from cart.models import Cart
# from products.serializers import ProductImageSerializer



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['name', 'mobile_number', 'email','created_at','updated_at']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description','product_code','color', 'offer_price_per_meter','created_at','updated_at']  # Add any other fields you need

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    product_code = serializers.CharField(source='product.product_code',read_only=True)
    product_color = serializers.CharField(source='product.color',read_only=True)
    free_product = ProductSerializer(required=False, allow_null=True)  # Handle free product as optional

    class Meta:
        model = OrderItem
        fields = ['product','product_code','product_color' ,'quantity', 'size', 'sleeve','length', 'price','free_product','created_at','updated_at']


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # User details should not be updated here
    shipping_address = AddressSerializer(read_only=True)  # Shipping address remains read-only
    items = OrderItemSerializer(many=True, read_only=True)  # Order items are not editable
    product_images = serializers.SerializerMethodField()


    class Meta:
        model = Order
        fields = [
            'id', 'user', 'shipping_address', 'total_price', 'status','Track_id','return_status','product_images',
            'payment_option', 'payment_status', 'created_at', 'items','rejected_reason'
        ]
        read_only_fields = ['id', 'user', 'total_price', 'created_at','updated_at', 'items']


    def get_product_images(self, obj):
        """
        Retrieve all product images related to the items in the order.
        """
        images = []
        for item in obj.items.all():
            product = item.product
            product_images = product.images.all()  # Assuming `ProductImage` is related to `Product` via `related_name="images"`
            for img in product_images:
                images.append(img.image.url)  # Include the image URL
        return images

class BulkOrderUpdateSerializer(serializers.Serializer):
    order_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text="List of order IDs to update."
    )
    status = serializers.ChoiceField(
        choices=Order.OrderStatus.choices,
        help_text="New status to set for the selected orders."
    )

class PaymentDetailsSerializer(serializers.ModelSerializer):
    user = UserSerializer()  # Serialize the user data

    class Meta:
        model = Order
        fields = ['id', 'user', 'total_price', 'payment_status', 'payment_option', 'created_at','updated_at']


class AdminOrderProductSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_details = serializers.SerializerMethodField()
    free_product_details = serializers.SerializerMethodField()

    class Meta:
        model = AdminOrderProduct
        fields = [
            'product_name',
            'quantity',
            'size',
            'sleeve',
            'custom_length',
            'length',
            'offer_type',
            'discount_amount',
            'total_price',
            'product_details',
            'free_product_details',
        ]

    def get_product_details(self, obj):
        """
        Retrieve detailed information about the product in the order.
        """
        product = obj.product
        return {
            "name": product.name,
            "product_code": product.product_code,
            "category_name": product.category.name,
            "description": product.description,
            "price_per_meter": product.offer_price_per_meter,
            "color": product.color,
        }

    def get_free_product_details(self, obj):
        """
        Retrieve detailed information about the free product in the order.
        """
        product = obj.free_product
        if product is None:
            return None
        return {
            "name": product.name,
            "product_code": product.product_code,
            "category_name": product.category.name,
            "description": product.description,
            "price_per_meter": product.offer_price_per_meter,
            "color": product.color,
        }


class AdminOrderSerializer(serializers.ModelSerializer):
    order_products = AdminOrderProductSerializer(many=True)

    class Meta:
        model = AdminOrder
        fields = [
            'id',
            'name',
            'phone_number',
            'address',
            'state',
            'pincode',
            'city',
            'district',
            'payment_method',
            'payment_status',
            'custom_status',
            'custom_return_status',
            'total_price',
            'custom_total_price',
            'created_at',
            'updated_at',
            'order_products',
            'Track_id',
            'Order_options',
            'rejected_reason',
            'is_VIP',
            'is_favourite'
        ]

class AdminUserOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminOrder
        fields = ['id','name', 'phone_number', 'address','is_favourite','is_VIP']