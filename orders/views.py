from decimal import Decimal,ROUND_DOWN
from django.conf import settings
from django.forms import ValidationError
import razorpay
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsAdminOrStaff
from .models import Order, OrderItem, TemporaryOrder,Return,ReturnItem,AdminReturn,AdminReturnItem
from .serializers import OrderSerializer,PaymentDetailsSerializer,AdminOrderSerializer,AdminUserOrderSerializer
from cart.models import Cart
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.shortcuts import get_object_or_404
from products.models import CategorySize, Product
from accounts.models import Address, CustomUser
from collections import defaultdict
from rest_framework.generics import RetrieveUpdateAPIView
from .models import AdminOrderProduct,AdminOrder
from rest_framework.exceptions import NotFound
from django.db import models
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.db.models import Sum


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

def calculate_price(product, order_length, quantity):
    """
    Calculate the total price based on the product's offer price per meter, order length, and quantity.
    """
    # Check if the product has an offer price per meter, otherwise use the base price
    price_per_meter = product.offer_price_per_meter if product.offer_price_per_meter else product.base_price_per_meter

    # Calculate the total price
    total_price = price_per_meter * Decimal(order_length) * Decimal(quantity)

    return total_price.quantize(Decimal('0.01'))

def validate_stock_length(product, order_length, quantity):
    """
    Validates if the product has sufficient stock length for the given order.
    """
    total_order_length = order_length * quantity
    if product.stock_length < total_order_length:
        raise ValidationError({"error": f"Insufficient stock for {product.name}"})
    return True

def get_free_products(product, order_length, quantity):
    """
    Retrieves free products eligible for a BOGO offer.
    Filters products with the same category and exact width as the provided product.
    """
    free_product_length = order_length * quantity

    # Filter products with the same category and exact width
    free_products = Product.objects.filter(
        category=product.category,
        width=product.width,  # Match the exact width of the given product
        is_out_of_stock=False,  # Only include products that are in stock
        stock_length__gte=free_product_length  # Ensure stock is sufficient
    )

    return free_products


class ValidateStockAndOfferView(APIView):
    """
    API endpoint to validate stock length and automatically handle BOGO offers.
    """
    permission_classes = [AllowAny]  # Allows access to anyone without authentication

    def post(self, request):
        product_id = request.data.get('product_id')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')
        quantity = request.data.get('quantity', 1)

        # Ensure all required fields are present
        if not product_id or not quantity:
            return Response({"error": "Product ID and quantity are required."}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)

        # Calculate order length based on size/sleeve or custom length
        if size and sleeve:
            category_size = product.category.sizes.filter(width=product.width).first()
            if not category_size:
                return Response({"error": "No matching category size found."}, status=status.HTTP_400_BAD_REQUEST)
            order_length = category_size.get_length(size, sleeve)
        elif custom_length:
            try:
                order_length = Decimal(custom_length)
            except ValueError:
                return Response({"error": "Invalid custom length."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Either size/sleeve or custom length is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not order_length:
            return Response({"error": "Invalid length selection."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate stock length
        try:
            validate_stock_length(product, order_length, quantity)
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Calculate total price
        total_price = calculate_price(product, order_length, quantity)

        # Check for BOGO offer
        if product.offer and product.offer.offer_type == 'BOGO':
            free_products = get_free_products(product, order_length, int(quantity))
            if free_products.exists():
                # Return available free products for selection
                free_products_data = [
                    {
                        "id": free_product.id,
                        "name": free_product.name,
                        "free prduct code":free_product.product_code,
                        "free_product_image": free_product.images.first().image.url if free_product.images.exists() else None,
                        "stock_length": str(free_product.stock_length),
                        "offer_price_per_meter": str(free_product.offer_price_per_meter),
                    }
                    for free_product in free_products
                ]
                return Response({
                    "message": "Stock is sufficient, and BOGO offer is applicable.",
                    "total_price": str(total_price),
                    "free_products": free_products_data,
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": "Stock is sufficient, but no free products available for the BOGO offer.",
                    "total_price": str(total_price),
                }, status=status.HTTP_200_OK)

        # If no BOGO offer applies, just return a success response
        return Response({
            "message": "Stock is sufficient, and no BOGO offer applies.",
            "total_price": str(total_price),
        }, status=status.HTTP_200_OK)

class DirectOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        product_id = request.data.get('product_id')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')
        quantity = int(request.data.get('quantity', 1))
        offer_product_id = request.data.get('offer_product_id')

        product = get_object_or_404(Product, id=product_id)

        if size and sleeve:
            category_size = product.category.sizes.filter(width=product.width).first()
            if not category_size:
                return Response({"error": "No matching category size found."}, status=status.HTTP_400_BAD_REQUEST)
            length = category_size.get_length(size, sleeve)
        elif custom_length:
            length = Decimal(custom_length)
        else:
            return Response({"error": "Either size/sleeve or custom length is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not length:
            return Response({"error": "Invalid length selection."}, status=status.HTTP_400_BAD_REQUEST)

        total_price = Decimal(product.offer_price_per_meter) * length * quantity
        offer_type = None
        discount_amount = Decimal("0.00")
        free_product_id = None

        if product.offer:
            if product.offer.offer_type == 'BOGO':
                free_product = offer_product_id
                if free_product:
                    offer_type = 'BOGO'
                    free_product_id = free_product
                    discount_amount = 0
            elif product.offer.offer_type == 'PERCENTAGE':
                offer_type = 'PERCENTAGE'
                discount_percentage = product.offer.discount_value
                discount_amount = total_price * (Decimal(discount_percentage) / 100)
                total_price -= discount_amount

        total_price = max(Decimal("0.00"), total_price)

        # Store the temporary order in the TemporaryOrder model
        temporary_order = TemporaryOrder.objects.create(
            user=user,
            product_id=product.id,
            quantity=quantity,
            size=size,
            sleeve=sleeve,
            custom_length=custom_length,
            length=length,
            price=total_price,
            offer_type=offer_type,
            discount_amount=discount_amount,
            free_product=free_product_id
        )

        return Response({
            "message": "Direct order placed. Proceed to checkout.",
            "temporary_order_id": temporary_order.id
        }, status=status.HTTP_201_CREATED)


    def get(self, request):
        """
        Retrieve the temporary order data stored in the TemporaryOrder model.
        """
        order_id = request.query_params.get('temporary_order_id')
        if not order_id:
            return Response({"error": "Temporary order ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            temporary_order = TemporaryOrder.objects.get(id=order_id)
        except TemporaryOrder.DoesNotExist:
            return Response({"error": "Temporary order not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve main product details
        try:
            main_product = Product.objects.get(id=temporary_order.product_id)
            main_product_name = main_product.name
            main_product_image = main_product.images.first().image.url if main_product.images.exists() else None
        except Product.DoesNotExist:
            return Response({"error": "Main product not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve free product details if applicable
        free_product_data = None
        if temporary_order.free_product:
            try:
                free_product = Product.objects.get(id=temporary_order.free_product)
                free_product_data = {
                    "id": free_product.id,
                    "name": free_product.name,
                    "image": free_product.images.first().image.url if free_product.images.exists() else None,
                    "quantity": temporary_order.quantity,  # Same as main product
                    "size": temporary_order.size,          # Same as main product
                    "sleeve": temporary_order.sleeve,      # Same as main product
                    "custom_length": temporary_order.custom_length  # Same as main product
                }
            except Product.DoesNotExist:
                pass  # Free product is optional; ignore if not found.

        # Prepare response data
        response_data = {
            "message": "Temporary order data retrieved successfully.",
            "order_item": {
                "main_product": {
                    "id": main_product.id,
                    "name": main_product_name,
                    "image": main_product_image,
                    "quantity": temporary_order.quantity,
                    "size": temporary_order.size,
                    "sleeve": temporary_order.sleeve,
                    "custom_length": temporary_order.custom_length,
                    "length": str(temporary_order.length),
                    "price": str(temporary_order.price),
                    "offer_type": temporary_order.offer_type,
                    "discount_amount": str(temporary_order.discount_amount),
                }
            }
        }

        # Add free product details if available
        if free_product_data:
            response_data["order_item"]["free_product"] = free_product_data

        return Response(response_data, status=status.HTTP_200_OK)


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        temporary_order_id = request.data.get('temporary_order_id')

        # Retrieve the temporary order
        try:
            temporary_order = TemporaryOrder.objects.get(id=temporary_order_id, user=user)
        except TemporaryOrder.DoesNotExist:
            return Response({"error": "No temporary order found."}, status=status.HTTP_400_BAD_REQUEST)

        address_id = request.data.get('address_id')
        payment_option = request.data.get('payment_option')
        address = get_object_or_404(Address, id=address_id, user=user)

        final_total = temporary_order.price
        final_total = max(Decimal("0.00"), final_total)

        if payment_option == 'Razorpay':
            razorpay_order = razorpay_client.order.create({
                "amount": int(final_total * 100),
                "currency": "INR",
                "payment_capture": "1"
            })
            return Response({
                "razorpay_order_id": razorpay_order['id'],
                "amount": final_total,
                "currency": "INR"
            }, status=status.HTTP_200_OK)

        elif payment_option == 'COD':
            order = self.create_order(user, address, final_total, temporary_order, payment_option)
            serializer = OrderSerializer(order)
            # Delete the temporary order after checkout
            temporary_order.delete()
            return Response({
                "message": "Order placed successfully with COD.",
                "order": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({"error": "Invalid payment option."}, status=status.HTTP_400_BAD_REQUEST)

    def create_order(self, user, address, total_price, temporary_order, payment_option):
        order = Order.objects.create(
            user=user,
            total_price=total_price,
            status='pending',
            shipping_address=address,
            payment_option=payment_option
        )

        # Main product handling
        product = get_object_or_404(Product, id=temporary_order.product_id)
        ordered_length = temporary_order.length * temporary_order.quantity
        if product.stock_length < ordered_length:
            raise ValidationError({"error": f"Insufficient stock for {product.name}"})

        # Deduct stock for the main product
        product.stock_length -= ordered_length
        product.save()

        # Free product handling (if applicable)
        free_product = None
        if temporary_order.free_product:
            free_product = get_object_or_404(Product, id=temporary_order.free_product)
            free_product_length = temporary_order.length * temporary_order.quantity

            if free_product.stock_length < free_product_length:
                raise ValidationError({"error": f"Insufficient stock for free product {free_product.name}"})

            # Deduct stock for the free product
            free_product.stock_length -= free_product_length
            free_product.save()

        # Create the order item
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=temporary_order.quantity,
            size=temporary_order.size,
            sleeve=temporary_order.sleeve,
            custom_length=temporary_order.custom_length,
            length=ordered_length,
            price=temporary_order.price,
            free_product=free_product  # This can be None if no free product
        )

        return order




class ListOrdersView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this endpoint
    serializer_class = OrderSerializer

    def get_queryset(self):
        """
        Return a list of orders based on the user's role.
        Admin and staff can view all orders, while regular users can only view their own orders.
        """
        user = self.request.user

        if user.is_staff or user.is_superuser:
            # Admins and staff can view all orders
            return Order.objects.all()

        # Regular users can only view their own orders
        return Order.objects.filter(user=user)

    def get(self, request, *args, **kwargs):
        """
        List all orders for admin/staff or only user's orders for regular users.
        """
        orders = self.get_queryset()
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ActiveAndPastOrdersView(generics.ListAPIView):
    """
    API view to list active and past (completed) orders based on order status.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return active or past orders based on a query parameter.
        Active orders are orders not yet completed.
        Past orders are completed orders.
        """
        user = self.request.user
        status_filter = self.request.query_params.get('status', 'active')  # Default to active orders

        if user.is_staff or user.is_superuser:
            # Admin/staff can view all orders
            queryset = Order.objects.all()
        else:
            # Regular users can only view their own orders
            queryset = Order.objects.filter(user=user)

        if status_filter == 'active':
            # Filter for active orders (exclude completed orders)
            queryset = queryset.exclude(status=Order.OrderStatus.COMPLETED)
        elif status_filter == 'past':
            # Filter for past (completed) orders
            queryset = queryset.filter(status=Order.OrderStatus.COMPLETED)

        return queryset.order_by('-id')

    def get(self, request, *args, **kwargs):
        """
        Return a list of active or past orders.
        Use 'status=active' or 'status=past' as query parameters.
        """
        orders = self.get_queryset()
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Handle retrieving, updating, and deleting a specific order.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Admin and staff users can access all orders.
        Regular users can only access their own orders.
        """
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Order.objects.all()  # Admin/staff can view any order
        return Order.objects.filter(user=user)  # Regular users can only view their own orders

    def get_object(self):
        """
        Ensure users can only access their own orders unless they are admin or staff.
        """
        queryset = self.get_queryset()
        order = get_object_or_404(queryset, id=self.kwargs['pk'])
        return order

    def get(self, request, *args, **kwargs):
        """
        Retrieve a specific order.
        """
        order = self.get_object()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        """
        Update a specific order.
        """
        order = self.get_object()
        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """
        Delete a specific order.
        """
        order = self.get_object()
        order.delete()
        return Response({"detail": "Order deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class OrderUpdateView(RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)  # Determine if it's a partial update
        instance = self.get_object()  # Retrieve the specific order instance
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            serializer.save()  # Save updated order details
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class BulkOrderUpdateView(APIView):
    """
    API endpoint for bulk updating order statuses.
    """
    permission_classes = [IsAdminOrStaff]

    def patch(self, request, *args, **kwargs):
        """
        Partially update multiple orders.
        """
        order_ids = request.data.get("order_ids")
        new_status = request.data.get("status")

        # Validate input
        if not order_ids or not new_status:
            return Response(
                {"error": "Both 'order_ids' and 'status' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the new status
        valid_statuses = [choice[0] for choice in Order.OrderStatus.choices]
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Valid options are: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update orders
        orders = Order.objects.filter(id__in=order_ids)
        if not orders.exists():
            return Response(
                {"error": "No orders found with the given IDs."},
                status=status.HTTP_404_NOT_FOUND,
            )

        updated_count = orders.update(status=new_status)

        return Response(
            {"message": f"Successfully updated {updated_count} orders to '{new_status}'."},
            status=status.HTTP_200_OK,
        )

class ReturnOrderListView(generics.ListAPIView):
    """
    API view to list all orders with status 'RETURN'.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(status=Order.OrderStatus.RETURN)

class PaymentDetailsListView(generics.ListAPIView):
    """
    API view to list payment details from the Order model.
    """
    serializer_class = PaymentDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.all()



class AdminOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        # Extract customer and address details
        name = data.get('name')
        phone_number = data.get('phone_number')
        address = data.get('address')
        state = data.get('state')
        pincode = data.get('pincode')
        city = data.get('city')
        district = data.get('district')

        # Extract payment details
        Track_id = data.get('Track_id')
        custom_total_price = data.get('custom_total_price')
        Order_options=data.get('Order_options')
        payment_method = data.get('payment_method')
        payment_status = data.get('payment_status')

        # Validate payment status
        valid_payment_status = ['Pending', 'Paid']
        if payment_status not in valid_payment_status:
            return Response({"error": "Invalid payment status."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the AdminOrder with an initial total_price of 0
        admin_order = AdminOrder.objects.create(
            name=name,
            phone_number=phone_number,
            address=address,
            state=state,
            pincode=pincode,
            city=city,
            district=district,
            Track_id=Track_id,
            payment_method=payment_method,
            payment_status=payment_status,
            Order_options=Order_options,
            custom_total_price=custom_total_price,
            total_price=Decimal("0.00")  # Set a default value for total_price
        )

        # Process products
        total_price = Decimal("0.00")
        products_data = data.get('products', [])
        for product_data in products_data:
            product_code = product_data.get('product_code')
            free_product_code = product_data.get('free_product_code')
            quantity = int(product_data.get('quantity', 1))
            size = product_data.get('size')
            sleeve = product_data.get('sleeve')
            custom_length = product_data.get('custom_length')

            product = get_object_or_404(Product, product_code=product_code)

            # Determine the length based on size, sleeve, or custom length
            if size and sleeve:
                category_size = product.category.sizes.filter(width=product.width).first()
                if not category_size:
                    return Response({"error": f"No matching category size found for {product.name}."}, status=status.HTTP_400_BAD_REQUEST)
                length = category_size.get_length(size, sleeve)
            elif custom_length:
                try:
                    length = Decimal(custom_length)
                except ValueError:
                    return Response({"error": f"Invalid custom length for {product.name}."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": f"Either size/sleeve or custom length is required for {product.name}."}, status=status.HTTP_400_BAD_REQUEST)

            total_order_length = length * quantity
            if product.stock_length < total_order_length:
                return Response({"error": f"Insufficient stock for {product.name}."}, status=status.HTTP_400_BAD_REQUEST)

            # Calculate total price and discounts
            item_price = Decimal(product.offer_price_per_meter) * length * quantity
            discount_amount = Decimal("0.00")
            offer_type = None
            free_product = None

            if product.offer:
                if product.offer.offer_type == 'BOGO':
                    if free_product_code:
                        free_product = get_object_or_404(Product, product_code=free_product_code)
                        if free_product.stock_length < total_order_length:
                            return Response({"error": f"Insufficient stock for free product {free_product.name}."}, status=status.HTTP_400_BAD_REQUEST)
                    offer_type = 'BOGO'
                elif product.offer.offer_type == 'PERCENTAGE':
                    offer_type = 'PERCENTAGE'
                    discount_percentage = product.offer.discount_value
                    discount_amount = item_price * (Decimal(discount_percentage) / 100)
                    item_price -= discount_amount

            total_price += max(Decimal("0.00"), item_price)

            # Create AdminOrderProduct
            AdminOrderProduct.objects.create(
                admin_order=admin_order,
                product=product,
                quantity=quantity,
                size=size,
                sleeve=sleeve,
                custom_length=custom_length,
                length=length,
                free_product=free_product,
                offer_type=offer_type,
                discount_amount=discount_amount,
                total_price=item_price
            )

            # Deduct stock for the main product and free product
            product.stock_length -= total_order_length
            product.save()
            if free_product:
                free_product.stock_length -= total_order_length
                free_product.save()

        # Update total price for the order
        admin_order.total_price = total_price
        admin_order.save()

        serializer = AdminOrderSerializer(admin_order)
        return Response({
            "message": "Order created successfully.",
            "order_details": serializer.data
        }, status=status.HTTP_201_CREATED)


class AdminOrderListAPIView(generics.ListAPIView):
    queryset = AdminOrder.objects.all()
    serializer_class = AdminOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter the queryset based on query parameters:
        - Filter by `product_code`
        - Filter by `payment_status`
        """
        queryset = super().get_queryset()

        # Filter by product_code
        product_code = self.request.query_params.get('product_code', None)
        if product_code:
            queryset = queryset.filter(order_products__product__product_code=product_code)

        # Filter by payment_status
        payment_status = self.request.query_params.get('payment_status', None)
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset.distinct()

class AdminOrderUpdateAPIView(generics.UpdateAPIView):
    queryset = AdminOrder.objects.all()
    serializer_class = AdminOrderSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        """
        Override the get_object method to get the AdminOrder by its ID.
        Raise a NotFound exception if the object doesn't exist.
        """
        try:
            order_id = self.kwargs.get('pk')
            return AdminOrder.objects.get(pk=order_id)
        except AdminOrder.DoesNotExist:
            raise NotFound(detail="Order not found.")

    def perform_update(self, serializer):
        """
        Override perform_update to save the updated data after validation.
        """
        serializer.save()

class OrderAnalyticsView(APIView):
    """
    Returns the daily, weekly, and monthly analytics for products ordered.
    """

    def get(self, request):
        today = timezone.now().date()

        # Daily orders
        daily_orders = (
            Order.objects.filter(created_at__date=today)
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total_orders=Count('id'))
            .order_by('-day')
        )

        # Weekly orders
        weekly_orders = (
            Order.objects.filter(created_at__gte=today - timezone.timedelta(days=7))
            .annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(total_orders=Count('id'))
            .order_by('-week')
        )

        # Monthly orders
        monthly_orders = (
            Order.objects.filter(created_at__gte=today - timezone.timedelta(days=30))
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total_orders=Count('id'))
            .order_by('-month')
        )

        data = {
            "daily_orders": list(daily_orders),
            "weekly_orders": list(weekly_orders),
            "monthly_orders": list(monthly_orders),
        }

        return Response(data, status=status.HTTP_200_OK)

class DashboardView(APIView):
    """
    Combined API to return various metrics and analytics for orders, users, payments, and profit calculations.
    """

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()
        start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Today orders count
        today_orders_count = Order.objects.filter(created_at__date=today).count() + \
                             AdminOrder.objects.filter(created_at__date=today).count()

        # Last 7 days orders count
        last_7_days_orders = (
            Order.objects.filter(created_at__gte=today - timezone.timedelta(days=7))
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total_orders=Count('id'))
            .order_by('-day')
        )

        # Today received amount
        today_received_amount = Order.objects.filter(
            created_at__date=today,
            payment_status=Order.PaymentStatus.PAID,
        ).aggregate(total=Sum('total_price'))['total'] or 0

        admin_today_received_amount = AdminOrder.objects.filter(
            created_at__date=today,
            payment_status=AdminOrder.PaymentStatus.PAID,
        ).aggregate(total=Sum('total_price'))['total'] or 0

        today_received_amount += admin_today_received_amount

        # Today cash on delivery orders
        today_cod_orders = Order.objects.filter(
            created_at__date=today,
            payment_option=Order.PaymentOptions.COD,
            payment_status=Order.PaymentStatus.PAID,
        ).count() + AdminOrder.objects.filter(
            created_at__date=today,
            payment_method=AdminOrder.PaymentOptions.COD,
            payment_status=AdminOrder.PaymentStatus.PAID,
        ).count()

        # Today shop orders (admin orders)
        today_shop_orders = AdminOrder.objects.filter(created_at__date=today).count()

        # Today online payment orders
        today_online_payment_orders = Order.objects.filter(
            created_at__date=today,
            payment_option=Order.PaymentOptions.RAZORPAY,
            payment_status=Order.PaymentStatus.PAID,
        ).count() + AdminOrder.objects.filter(
            created_at__date=today,
            payment_method=AdminOrder.PaymentOptions.RAZORPAY,
            payment_status=AdminOrder.PaymentStatus.PAID,
        ).count()

        # 1. Total Products
        total_products = Product.objects.count()

        # 2. Total Orders (user and admin orders combined)
        total_orders = Order.objects.count() + AdminOrder.objects.count()

        total_users = CustomUser.objects.filter(is_staff=False, is_superuser=False).count()

        # 3. Order Status Counts (both user and admin orders)
        status_counts = Order.objects.values('status').annotate(count=Count('id'))

        # For Admin Orders, use 'payment_status' field instead of 'status'
        admin_status_counts = AdminOrder.objects.values('payment_status').annotate(count=Count('id'))

        # Merge both results into one dictionary
        combined_status_counts = {}

        # Add counts from user orders
        for item in status_counts:
            combined_status_counts[item['status']] = item['count']

        # Add counts from admin orders, merging into the same dictionary
        for item in admin_status_counts:
            # Use 'payment_status' for admin orders
            status = item['payment_status']
            if status in combined_status_counts:
                combined_status_counts[status] += item['count']
            else:
                combined_status_counts[status] = item['count']

        # 4. Payment Status Counts (both user and admin orders)
        payment_status_counts = Order.objects.values('payment_status').annotate(count=Count('id'))
        admin_payment_status_counts = AdminOrder.objects.values('payment_status').annotate(count=Count('id'))
        combined_payment_status_counts = {item['payment_status']: item['count'] for item in list(payment_status_counts) + list(admin_payment_status_counts)}

        # 5. Payment Method Counts (both user and admin orders)
        payment_method_counts = Order.objects.values('payment_option').annotate(count=Count('id'))

        # For Admin Orders, use 'payment_method' instead of 'payment_option'
        admin_payment_method_counts = AdminOrder.objects.values('payment_method').annotate(count=Count('id'))

        # Merge both results into one dictionary
        combined_payment_method_counts = {}

        # Add counts from user orders
        for item in payment_method_counts:
            combined_payment_method_counts[item['payment_option']] = item['count']

        # Add counts from admin orders, merging into the same dictionary
        for item in admin_payment_method_counts:
            # Use 'payment_method' for admin orders
            payment_method = item['payment_method']
            if payment_method in combined_payment_method_counts:
                combined_payment_method_counts[payment_method] += item['count']
            else:
                combined_payment_method_counts[payment_method] = item['count']

        # 6. Total Received Amount (from user and admin orders)
        user_received_amount = Order.objects.filter(payment_status=Order.PaymentStatus.PAID).aggregate(total_received=Sum('total_price'))['total_received'] or 0
        admin_received_amount = AdminOrder.objects.filter(payment_status=AdminOrder.PaymentStatus.PAID).aggregate(total_received=Sum('total_price'))['total_received'] or 0
        user_refunds = ReturnItem.objects.aggregate(total_refund=Sum('refund_price'))['total_refund'] or 0
        net_revenue = user_received_amount + admin_received_amount
        total_received_amount = net_revenue - user_refunds

        # 7. Total Invested Amount
        total_invested_amount = Product.objects.aggregate(total_invested=Sum('invested_amount'))['total_invested'] or 0

        # 8. Profit Calculation
        profit = total_received_amount - total_invested_amount

        # 9. Total User Orders
        total_user_orders = Order.objects.filter(user__isnull=False, status__in=[Order.OrderStatus.ACCEPT, Order.OrderStatus.COMPLETED]).count()

        # 10. Total Admin Orders
        total_admin_orders = AdminOrder.objects.count()

        # 11. Total COD Orders by User
        total_cod_user_orders = Order.objects.filter(payment_option=Order.PaymentOptions.COD, payment_status=Order.PaymentStatus.PAID, status__in=[Order.OrderStatus.ACCEPT, Order.OrderStatus.COMPLETED]).count()

        # 12. Total COD Orders by Admin
        total_cod_admin_orders = AdminOrder.objects.filter(payment_method=AdminOrder.PaymentOptions.COD, payment_status=AdminOrder.PaymentStatus.PAID).count()

        # 13. Total Online Payment Orders by User
        total_online_user_orders = Order.objects.filter(payment_option=Order.PaymentOptions.RAZORPAY, payment_status=Order.PaymentStatus.PAID, status__in=[Order.OrderStatus.ACCEPT, Order.OrderStatus.COMPLETED]).count()

        # 14. Total Online Payment Orders by Admin
        total_online_admin_orders = AdminOrder.objects.filter(payment_method=AdminOrder.PaymentOptions.RAZORPAY, payment_status=AdminOrder.PaymentStatus.PAID).count()

        # 15. Orders by District (User and Admin combined)
        user_orders_by_district = Order.objects.filter(status__in=[Order.OrderStatus.ACCEPT, Order.OrderStatus.COMPLETED]).values('shipping_address__district').annotate(order_count=Count('id'))
        # Orders by district including admin order products
        admin_orders_by_district = (
            AdminOrder.objects.prefetch_related('order_products')
            .values('district')
            .annotate(order_count=Count('id'))
        )

        combined_orders_by_district = list(user_orders_by_district) + list(admin_orders_by_district)
        district_order_count = {}
        for order in combined_orders_by_district:
            district = order.get('shipping_address__district', order.get('district'))
            count = order['order_count']
            district_order_count[district] = district_order_count.get(district, 0) + count

        # Prepare the data for the response
        data = {
            "today_orders_count": today_orders_count,
            "last_7_days_orders": list(last_7_days_orders),
            "today_received_amount": today_received_amount,
            "today_cod_orders": today_cod_orders,
            "today_shop_orders": today_shop_orders,
            "today_online_payment_orders": today_online_payment_orders,
            "total_products": total_products,
            "total_users":total_users,
            "total_orders": total_orders,
            "status_counts": combined_status_counts,
            "payment_status_counts": combined_payment_status_counts,
            "payment_method_counts": combined_payment_method_counts,
            "total_received_amount": total_received_amount,
            "total_invested_amount": total_invested_amount,
            "profit": profit,
            "total_user_orders": total_user_orders,
            "total_admin_orders": total_admin_orders,
            "total_cod_user_orders": total_cod_user_orders,
            "total_cod_admin_orders": total_cod_admin_orders,
            "total_online_user_orders": total_online_user_orders,
            "total_online_admin_orders": total_online_admin_orders,
            "orders_by_district_combined": [
                {"district": district, "order_count": count}
                for district, count in district_order_count.items()
            ],
        }

        return Response(data)

class BulkAdminOrderUpdateView(APIView):
    """
    API endpoint for bulk updating AdminOrder statuses.
    """
    permission_classes = [IsAdminOrStaff]

    def patch(self, request, *args, **kwargs):
        """
        Partially update multiple AdminOrder instances.
        """
        order_ids = request.data.get("order_ids")
        new_status = request.data.get("status")

        # Validate input
        if not order_ids or not new_status:
            return Response(
                {"error": "Both 'order_ids' and 'status' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the new status
        valid_statuses = [choice[0] for choice in AdminOrder.OrderStatus.choices]
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Valid options are: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update AdminOrder instances
        admin_orders = AdminOrder.objects.filter(id__in=order_ids)
        if not admin_orders.exists():
            return Response(
                {"error": "No AdminOrder instances found with the given IDs."},
                status=status.HTTP_404_NOT_FOUND,
            )

        updated_count = admin_orders.update(custom_status=new_status)

        return Response(
            {"message": f"Successfully updated {updated_count} AdminOrder instances to '{new_status}'."},
            status=status.HTTP_200_OK,
        )

class AdminUserOrderListView(generics.ListAPIView):
    permission_classes = [IsAdminOrStaff]
    queryset = AdminOrder.objects.all()
    serializer_class = AdminUserOrderSerializer


class ProcessReturnView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Handles product returns for an order. Updates product stock, saves refund details,
        and associates return data with the order using product codes.
        """
        order_id = kwargs.get("order_id")
        order = get_object_or_404(Order, id=order_id)

        # Validate order status
        if order.status != Order.OrderStatus.RETURN:
            return Response(
                {"error": "Order status must be 'Return' to process returns."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return_data = request.data.get("returns", [])
        if not return_data:
            return Response(
                {"error": "No return data provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_refund = 0

        try:
            with transaction.atomic():
                # Create parent return entry
                return_request = Return.objects.create(
                    order=order,
                    user=order.user,
                )

                for item in return_data:
                    product_code = item.get("product_code")
                    returned_length = item.get("returned_length", 0)

                    # Retrieve the associated product and order item based on product code (string)
                    product = get_object_or_404(Product, product_code=product_code)
                    order_item = get_object_or_404(OrderItem, order=order, product=product)

                    # Validate returned length
                    if returned_length > order_item.length:
                        raise ValueError(
                            f"Returned length {returned_length} exceeds ordered length {order_item.length} for product code {product_code}."
                        )

                    # Calculate refund price per meter
                    price_per_meter = order_item.price / order_item.length

                    # Ensure returned_length is a Decimal for precise calculation
                    returned_length_decimal = Decimal(returned_length)

                    # Calculate refund price
                    refund_price = round(price_per_meter * returned_length_decimal, 2)

                    # Update product stock
                    if returned_length > 0:
                        product.stock_length += Decimal(returned_length)
                        product.save()

                    # Add to total refund
                    total_refund += refund_price

                    # Create ReturnItem entry
                    ReturnItem.objects.create(
                        return_request=return_request,
                        product=product,
                        returned_length=returned_length,
                        refund_price=refund_price,
                        restocked=True,
                    )

                # Update order's return status
                order.return_status = Order.ReturnStatus.COMPLETED
                order.save()

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Return processed successfully.",
                "total_refund": total_refund,
                "return_id": return_request.id,
            },
            status=status.HTTP_200_OK,
        )


class ReturnProductsView(APIView):
    """
    API view to filter orders with status 'Return' and retrieve all associated returned products,
    including shipping address and return creation details.
    """
    permission_classes = [IsAdminOrStaff]


    def get_product_images(self, product):
        """
        Helper method to retrieve product images.
        Assumes the product model has a related `images` field.
        """
        return [image.image.url for image in product.images.all()]

    def get(self, request, *args, **kwargs):
        # Filter orders with status == 'Return'
        returned_orders = Order.objects.filter(status=Order.OrderStatus.RETURN)

        if not returned_orders.exists():
            return Response({"message": "No orders with status 'Return' found."}, status=404)

        # Prefetch related returns and return items
        data = []
        for order in returned_orders.prefetch_related("returns__items"):
            user = order.user
            user_data = {
                "name": user.name,  # Assuming the user model has a 'name' field
                "mobile_number": user.mobile_number,  # Assuming the user model has a 'mobile_number' field
            }

            ordered_product_details = []
            for ordered_product in order.items.all():
                product = ordered_product.product
                ordered_product_details.append({
                    "id": product.id,
                    "product_name": product.name,
                    "description": product.description,
                    "product_code": product.product_code,  # Assuming product has a product_code field
                    "product_color": product.color,  # Assuming product has a color field
                    "offer_price_per_meter": product.offer_price_per_meter,  # Assuming offer price exists
                    "quantity": ordered_product.quantity,
                    "size": ordered_product.size,  # Assuming size is part of ordered product
                    "sleeve": ordered_product.sleeve,  # Assuming sleeve is part of ordered product
                    "length": ordered_product.length,  # Assuming length is part of ordered product
                    "price": str(ordered_product.price),
                    "free_product": {
                        "id": ordered_product.free_product.id,
                        "name": ordered_product.free_product.name,
                        "product_code": ordered_product.free_product.product_code,
                    } if ordered_product.free_product else None,
                    "product_images": self.get_product_images(product),  # Fetch product images
                    "created_at": ordered_product.created_at.isoformat(),
                    "updated_at": ordered_product.updated_at.isoformat(),
                })

            # Get the shipping address for the order
            shipping_address = order.shipping_address
            address_data = None
            if shipping_address:
                address_data = {
                    "name": shipping_address.name,
                    "email": shipping_address.email,
                    "mobile_number": shipping_address.mobile_number,
                    "address": shipping_address.address,
                    "pincode": shipping_address.pincode,
                    "district": shipping_address.district,
                    "state": shipping_address.state,
                    "country": shipping_address.country,
                }

            # Prepare order data
            order_data = {
                "order_id": order.id,
                "user": user_data,
                "payment status":order.payment_status,
                "paymet method":order.payment_option,
                "order status":order.status,
                "total_price": order.total_price,
                "Track_id":order.Track_id,
                "updated at":order.updated_at,
                "shipping_address": address_data,
                "ordered product details":ordered_product_details,
                "returns": [],
            }

            # Fetch associated returns and their items
            for return_request in order.returns.all():
                return_data = {
                    "return_id": return_request.id,
                    "created_at": return_request.created_at,  # Return creation time
                    "items": []
                }

                for item in return_request.items.all():
                    return_data["items"].append({
                        "return product code":item.product.product_code,
                        "product_name": item.product.name,
                        "returned_length": item.returned_length,
                        "refund_price": item.refund_price,
                    })

                order_data["returns"].append(return_data)

            data.append(order_data)

        return Response(data, status=200)



class AdminOrderProcessReturnView(APIView):
    """
    Handles product returns for an AdminOrder. Updates product stock, calculates refunds,
    and associates return data with the admin order.
    """
    permission_classes = [IsAdminOrStaff]

    def post(self, request, *args, **kwargs):
        admin_order_id = kwargs.get("admin_order_id")
        admin_order = get_object_or_404(AdminOrder, id=admin_order_id)

        # Validate admin order status
        if admin_order.custom_status != AdminOrder.OrderStatus.RETURN:
            return Response(
                {"error": "Order status must be 'Return' to process returns."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return_data = request.data.get("returns", [])
        if not return_data:
            return Response(
                {"error": "No return data provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_refund = Decimal(0)

        try:
            with transaction.atomic():
                # Create a parent return entry
                return_request = AdminReturn.objects.create(
                    order=admin_order
                )

                for item in return_data:
                    product_code = item.get("product_code")
                    returned_length = item.get("returned_length", 0)

                    # Retrieve the associated product and admin order product
                    product = get_object_or_404(Product, product_code=product_code)
                    admin_order_product = get_object_or_404(AdminOrderProduct, admin_order=admin_order, product=product)

                    # Validate returned length
                    if returned_length > admin_order_product.length:
                        raise ValueError(
                            f"Returned length {returned_length} exceeds ordered length {admin_order_product.length} for product ID {product_code}."
                        )

                    # Calculate refund price per meter
                    price_per_meter = admin_order_product.total_price / admin_order_product.length

                    # Ensure returned_length is a Decimal for precise calculation
                    returned_length_decimal = Decimal(returned_length)

                    # Calculate refund price
                    refund_price = round(price_per_meter * returned_length_decimal, 2)

                    # Update product stock
                    if returned_length > 0:
                        product.stock_length += returned_length_decimal
                        product.save()

                    # Add to total refund
                    total_refund += refund_price

                    # Create AdminReturnItem entry
                    AdminReturnItem.objects.create(
                        return_request=return_request,
                        product=product,
                        returned_length=returned_length_decimal,
                        refund_price=refund_price,
                        restocked=True,
                    )

                # Update admin order's return status
                admin_order.custom_return_status = AdminOrder.ReturnStatus.COMPLETED
                admin_order.save()

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Return processed successfully.",
                "total_refund": str(total_refund),  # Convert to string to ensure JSON serialization
                "return_id": return_request.id,
            },
            status=status.HTTP_200_OK,
        )


class AdminOrderReturnProductsView(APIView):
    """
    API view to filter AdminOrders with status 'Return' and retrieve all associated returned products,
    including customer details and address.
    """
    permission_classes = [IsAdminOrStaff]

    def get_product_images(self, product):
        """
        Helper method to retrieve product images.
        Assumes the product model has a related `images` field.
        """
        return [image.image.url for image in product.images.all()]

    def get(self, request, *args, **kwargs):
        # Filter admin orders with status == 'Return'
        returned_admin_orders = AdminOrder.objects.filter(
            custom_status=AdminOrder.OrderStatus.RETURN
        ).prefetch_related("returns__items__product")

        if not returned_admin_orders.exists():
            return Response(
                {"message": "No admin orders with status 'Return' found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Serialize data
        data = []
        for admin_order in returned_admin_orders:
            ordered_product_details = []
            for ordered_product in admin_order.order_products.all():
                product = ordered_product.product
                ordered_product_details.append({
                    "id": product.id,
                    "product_name": product.name,
                    "description": product.description,
                    "product_code": product.product_code,  # Assuming product has a product_code field
                    "product_color": product.color,  # Assuming product has a color field
                    "offer_price_per_meter": product.offer_price_per_meter,  # Assuming offer price exists
                    "quantity": ordered_product.quantity,
                    "size": ordered_product.size,  # Assuming size is part of ordered product
                    "sleeve": ordered_product.sleeve,  # Assuming sleeve is part of ordered product
                    "length": ordered_product.length,  # Assuming length is part of ordered product
                    "total_price": ordered_product.total_price,
                    "free_product": {
                        "id": ordered_product.free_product.id,
                        "name": ordered_product.free_product.name,
                        "product_code": ordered_product.free_product.product_code,
                    } if ordered_product.free_product else None,
                    "product_images": self.get_product_images(product),
                })
            admin_order_data = {
                "admin_order_id": admin_order.id,
                "customer_name": admin_order.name,
                "phone_number": admin_order.phone_number,
                "updated_at":admin_order.updated_at,
                "ordered product details":ordered_product_details,
                "Track_id":admin_order.Track_id,
                "custom_status":admin_order.custom_status,
                "payment_method":admin_order.payment_method,
                "payment_status":admin_order.payment_status,
                "Order_options":admin_order.Order_options,
                "address": {
                    "street_address": admin_order.address,
                    "city": admin_order.city,
                    "district": admin_order.district,
                    "state": admin_order.state,
                    "pincode": admin_order.pincode,
                },
                "total_price": str(admin_order.total_price),
                "custom_price":admin_order.custom_total_price,
                "returns": []
            }

            # Fetch associated returns and their items
            for return_request in admin_order.returns.all():
                return_data = {
                    "return_id": return_request.id,
                    "created_at": return_request.created_at.isoformat(),
                    "items": []
                }

                for item in return_request.items.all():
                    return_data["items"].append({
                        "product_name": item.product.name,
                        "product_code": item.product.product_code,
                        "returned_length": str(item.returned_length),
                        "refund_price": str(item.refund_price),
                    })

                admin_order_data["returns"].append(return_data)

            data.append(admin_order_data)

        return Response(data, status=status.HTTP_200_OK)
