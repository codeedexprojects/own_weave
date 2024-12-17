from django.db import models
from django.conf import settings
from accounts.models import Address
from products.models import Product, CategorySize

class Order(models.Model):
    class PaymentOptions(models.TextChoices):
        COD = 'COD', 'Cash on Delivery'
        RAZORPAY = 'Razorpay', 'Online Payment'

    class PaymentStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        PAID = 'Paid', 'Paid'
        FAILED = 'Failed', 'Failed'

    class ReturnStatus(models.TextChoices):
        RETURN_INITIATED = 'Return Initiated','Return Initiated'
        PENDING = 'Pending','Pending'
        COMPLETED = 'Completed','Completed'

    class OrderStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPT = 'Accept','Accept'
        REJECT = 'Reject','Reject'
        RETURN = 'Return','Return'
        COMPLETED = 'Completed','Completed'
        # PROCESSING = 'processing', 'Processing'
        # SHIPPED = 'shipped', 'Shipped'
        # DELIVERED = 'delivered', 'Delivered'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    Track_id = models.CharField(max_length=200,null=True,blank=True)
    return_status = models.CharField(max_length=20, choices=ReturnStatus.choices,null=True,blank=True)
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL,null=True)
    payment_option = models.CharField(max_length=10, choices=PaymentOptions.choices)
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PAID)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    razorpay_order_id = models.CharField(max_length=100,null=True,blank=True)
    rejected_reason = models.TextField(null=True,blank=True)




    def __str__(self):
        return f"Order {self.id} for {self.user}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=6, null=True, blank=True, choices=CategorySize.SIZE_CHOICES, help_text="Select size (L, XL, XXL, etc.)")
    sleeve = models.CharField(max_length=10, null=True, blank=True, choices=CategorySize.SLEEVE_CHOICES, help_text="Select sleeve type (full, half, etc.)")
    custom_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    free_product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="order_item_free_product")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.size}, {self.sleeve})"

class TemporaryOrder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product_id = models.PositiveIntegerField()  # Reference to the product
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=6, null=True, blank=True)
    sleeve = models.CharField(max_length=10, null=True, blank=True)
    custom_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_type = models.CharField(max_length=20, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    free_product = models.PositiveIntegerField(null=True, blank=True)  # If there's a free product (reference to product ID)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Temporary order for {self.user} on product {self.product_id}"

class AdminOrder(models.Model):
    class PaymentOptions(models.TextChoices):
        COD = 'COD', 'Cash on Delivery'
        RAZORPAY = 'Razorpay', 'Online Payment'
        SHOPPAYMENT='ShopPayment','ShopPayment'

    class PaymentStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        PAID = 'Paid', 'Paid'
        FAILED = 'Failed', 'Failed'

    class orderoptions(models.TextChoices):
        Online = 'True', 'Online'
        Shop = 'False', 'Shop'


    class OrderStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPT = 'Accept','Accept'
        REJECT = 'Reject','Reject'
        RETURN = 'Return','Return'
        COMPLETED = 'Completed','Completed'

    class ReturnStatus(models.TextChoices):
        RETURN_INITIATED = 'Return Initiated','Return Initiated'
        PENDING = 'Pending','Pending'
        COMPLETED = 'Completed','Completed'

    name = models.CharField(max_length=100, help_text="Name of the customer")
    phone_number = models.CharField(max_length=15, help_text="Customer's contact number")
    address = models.TextField(help_text="Customer's address")
    state = models.CharField(max_length=100, help_text="State",null=True,blank=True)
    pincode = models.CharField(max_length=6, help_text="Pincode",null=True,blank=True)
    custom_status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    custom_return_status = models.CharField(max_length=20, choices=ReturnStatus.choices,null=True,blank=True)
    city = models.CharField(max_length=100, help_text="City",null=True,blank=True)
    district = models.CharField(max_length=100, help_text="District",null=True,blank=True)
    Track_id = models.CharField(max_length=200,null=True,blank=True)
    payment_method = models.CharField(max_length=12, choices=PaymentOptions.choices, help_text="Payment method")
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, help_text="Payment status")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total price of the order")
    custom_total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, help_text="Order creation timestamp")
    updated_at = models.DateTimeField(auto_now=True)
    rejected_reason = models.TextField(null=True,blank=True)
    Order_options = models.CharField(max_length=10, choices=orderoptions.choices, default=orderoptions.Shop)
    is_favourite = models.BooleanField(default=False)
    is_VIP = models.BooleanField(default=False)

    def __str__(self):
        return f"Order {self.id} for {self.name}"


class AdminOrderProduct(models.Model):
    admin_order = models.ForeignKey(AdminOrder, on_delete=models.CASCADE, related_name="order_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=6, null=True, blank=True, choices=CategorySize.SIZE_CHOICES)
    sleeve = models.CharField(max_length=10, null=True, blank=True, choices=CategorySize.SLEEVE_CHOICES)
    custom_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    free_product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="admin_order_free_product")
    offer_type = models.CharField(max_length=20, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} in order {self.admin_order.id}"



class Return(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='returns', help_text="Associated order")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, help_text="User who placed the order")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Return request created at")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Return for Order {self.order.id}"


class ReturnItem(models.Model):
    return_request = models.ForeignKey(Return, on_delete=models.CASCADE, related_name="items", help_text="Associated return request")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, help_text="Product being returned")
    returned_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Returned length (if applicable)")
    refund_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Refunded price (if applicable)")
    restocked = models.BooleanField(default=False, help_text="Has the stock been updated for this return item?")
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Returned {self.product.name}"


class AdminReturn(models.Model):
    order = models.ForeignKey('AdminOrder', on_delete=models.CASCADE, related_name='returns', help_text="Associated order")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Return request created at")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Return for Order {self.order.id}"


class AdminReturnItem(models.Model):
    return_request = models.ForeignKey(AdminReturn, on_delete=models.CASCADE, related_name="items", help_text="Associated return request")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, help_text="Product being returned")
    returned_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Returned length (if applicable)")
    refund_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Refunded price (if applicable)")
    restocked = models.BooleanField(default=False, help_text="Has the stock been updated for this return item?")
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Returned {self.product.name}"
