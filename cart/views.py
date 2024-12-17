from decimal import Decimal
import razorpay
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from accounts.models import Address
from accounts.serializers import AddressSerializer
from orders.models import Order, OrderItem
from .serializers import OrderSerializer
from orders.views import get_free_products, validate_stock_length
from products.models import Product
from .models import Cart, CartItem
from .serializers import CartSerializer
from django.db.models import Sum
from django.http import JsonResponse


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

class CartItemCountView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            # If user is not authenticated, return 0 items in the cart
            return Response({"cart_item_count": 0}, status=200)

        try:
            # If user is authenticated, fetch the cart and its item count
            cart = Cart.objects.get(user=request.user)
            cart_item_count = CartItem.objects.filter(cart=cart).count()
            return Response({"cart_item_count": cart_item_count}, status=200)
        except Cart.DoesNotExist:
            # If no cart is found, return 0 items
            return Response({"cart_item_count": 0}, status=200)



class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve the current user's cart and its items, including free product details if applicable."""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        response_data = []
        for item in cart_items:
            main_product = {
                "id": item.product.id,
                "name": item.product.name,
                "image": item.product.images.first().image.url if item.product.images.exists() else None,
                "quantity": item.quantity,
                "size": item.size,
                "sleeve": item.sleeve,
                "custom_length": item.custom_length,
                "length": str(item.length),
                "price": str(item.price),
                "offer_type": item.offer_type,
                "discount_amount": str(item.discount_amount),
            }

            free_product = None
            if item.free_product:
                free_product = {
                    "id": item.free_product.id,
                    "name": item.free_product.name,
                    "image": item.free_product.images.first().image.url if item.free_product.images.exists() else None,
                    "quantity": item.quantity,  # Free product quantity
                    "size": item.size,
                    "sleeve": item.sleeve,
                    "custom_length": item.custom_length,
                    "length": str(item.length),
                }

            response_data.append({
                "id": item.id,  # Unique cart item ID
                "main_product": main_product,
                "free_product": free_product,
            })

        return Response({
            "message": "Cart retrieved successfully.",
            "cart_items": response_data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """Add an item to the cart with validations for stock and offers."""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')
        quantity = int(request.data.get('quantity', 1))
        offer_product_id = request.data.get('offer_product_id')

        product = get_object_or_404(Product, id=product_id)

        # Validate stock length
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

        try:
            validate_stock_length(product, order_length, quantity)
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Calculate price
        length = order_length
        price = Decimal(product.offer_price_per_meter) * length * quantity
        discount_amount = Decimal("0.00")
        offer_type = None
        free_product = None

        # Handle offers
        if product.offer and product.offer.offer_type == 'BOGO':
            if offer_product_id:
                try:
                    free_product = Product.objects.get(id=offer_product_id)
                except Product.DoesNotExist:
                    return Response({"error": "Invalid offer product ID."}, status=status.HTTP_400_BAD_REQUEST)
                offer_type = 'BOGO'
            else:
                return Response({"error": "BOGO offer requires a free product ID."}, status=status.HTTP_400_BAD_REQUEST)
        elif product.offer and product.offer.offer_type == 'PERCENTAGE':
            offer_type = 'PERCENTAGE'
            discount_percentage = product.offer.discount_value
            discount_amount = price * (Decimal(discount_percentage) / 100)

        # Create the main cart item
        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            size=size,
            sleeve=sleeve,
            custom_length=custom_length,
            length=length,
            price=price - discount_amount,
            discount_amount=discount_amount,
            offer_type=offer_type,
            free_product=free_product,
        )

        return Response({"message": "Item added to cart"}, status=status.HTTP_200_OK)


    def delete(self, request, item_id):
        """Remove a specific item from the cart."""
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        return Response({"message": "Item removed from cart"}, status=status.HTTP_200_OK)

    def delete_all(self, request):
        """Clear all items from the cart."""
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()
        return Response({"message": "Cart cleared"}, status=status.HTTP_200_OK)


    def put(self, request, item_id):
        """Edit an existing cart item (replace the item)."""
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        # Get the new details from the request
        product_id = request.data.get('product_id')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')
        quantity = int(request.data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id)

        # Validate stock length
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

        try:
            validate_stock_length(product, order_length, quantity)
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Calculate price
        length = order_length
        price = Decimal(product.offer_price_per_meter) * length
        discount_amount = Decimal("0.00")
        offer_type = None

        # Handle offers
        if product.offer:
            if product.offer.offer_type == 'BOGO':
                offer_type = 'BOGO'
                free_products = get_free_products(product, order_length, quantity)
                if free_products.exists():
                    free_product = free_products.first()  # Take the first available free product
                    discount_amount = 0  # No discount on the main product, but BOGO applies
                    # Create cart item for the free product
                    CartItem.objects.create(
                        cart=cart,
                        product=free_product,
                        quantity=quantity,
                        size=size,
                        sleeve=sleeve,
                        custom_length=custom_length,
                        length=length,
                        price=0,  # Free product, so no cost
                        discount_amount=0,
                        offer_type='BOGO',
                    )
            elif product.offer.offer_type == 'PERCENTAGE':
                offer_type = 'PERCENTAGE'
                discount_percentage = product.offer.discount_percentage
                discount_amount = price * (Decimal(discount_percentage) / 100)

        # Update the cart item
        cart_item.product = product
        cart_item.size = size
        cart_item.sleeve = sleeve
        cart_item.custom_length = custom_length
        cart_item.quantity = quantity
        cart_item.length = length
        cart_item.price = price - discount_amount
        cart_item.discount_amount = discount_amount
        cart_item.offer_type = offer_type
        cart_item.save()

        return Response({"message": "Cart item updated successfully."}, status=status.HTTP_200_OK)

    def patch(self, request, item_id):
        """Partially update a cart item (e.g., update quantity, size, etc.)."""
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        # Update only the provided fields
        quantity = request.data.get('quantity')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')

        if quantity:
            cart_item.quantity = quantity
        if size:
            cart_item.size = size
        if sleeve:
            cart_item.sleeve = sleeve
        if custom_length:
            cart_item.custom_length = custom_length

        # Recalculate the price based on updated fields
        product = cart_item.product
        if size and sleeve:
            category_size = product.category.sizes.filter(width=product.width).first()
            order_length = category_size.get_length(size, sleeve)
        elif custom_length:
            order_length = Decimal(custom_length)
        else:
            return Response({"error": "Either size/sleeve or custom length is required."}, status=status.HTTP_400_BAD_REQUEST)

        cart_item.length = order_length
        price = Decimal(product.offer_price_per_meter) * order_length
        cart_item.price = price - cart_item.discount_amount

        cart_item.save()
        return Response({"message": "Cart item updated successfully."}, status=status.HTTP_200_OK)



class CheckoutCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Checkout the cart and create an order."""
        user = request.user
        cart = get_object_or_404(Cart, user=user)

        if not cart.items.exists():
            return Response({"error": "Cart is empty. Add items before checkout."}, status=status.HTTP_400_BAD_REQUEST)

        address_id = request.data.get('address_id')
        payment_option = request.data.get('payment_option')
        address = get_object_or_404(Address, id=address_id, user=user)

        # Calculate total price
        total_price = Decimal("0.00")
        for item in cart.items.all():
            total_price += item.price

            # Validate stock for each item
            try:
                validate_stock_length(item.product, item.length, item.quantity)
            except ValidationError as e:
                return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        if payment_option == 'Razorpay':
            # Create Razorpay order
            razorpay_order = razorpay_client.order.create({
                "amount": int(total_price * 100),  # Amount in paise
                "currency": "INR",
                "payment_capture": "1"
            })

            # Store the Razorpay order ID in the database for reference
            order = self.create_order(user, address, total_price, cart, payment_option)
            order.razorpay_order_id = razorpay_order['id']
            order.save()

            return Response({
                "user name":user.name,
                "mobile number":user.mobile_number,
                "razorpay_order_id": razorpay_order['id'],
                "amount": str(total_price),
                "currency": "INR",
                "message": "Razorpay order created successfully.",
            }, status=status.HTTP_200_OK)

        elif payment_option == 'COD':
            order = self.create_order(user, address, total_price, cart, payment_option)

            # Clear the cart for COD payment option
            cart.items.all().delete()

            serializer = OrderSerializer(order)
            return Response({
                "message": "Order placed successfully with COD.",
                "order": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({"error": "Invalid payment option."}, status=status.HTTP_400_BAD_REQUEST)

    def create_order(self, user, address, total_price, cart, payment_option):
        """Helper function to create an order."""
        order = Order.objects.create(
            user=user,
            total_price=total_price,
            shipping_address=address,
            payment_option=payment_option
        )

        for item in cart.items.all():
            # Deduct stock
            item.product.stock_length -= item.length * item.quantity
            item.product.save()

            # Create order item
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                size=item.size,
                sleeve=item.sleeve,
                custom_length=item.custom_length,
                length=item.length,
                price=item.price,
                free_product=item.free_product,
            )

            if item.free_product:
                # Deduct stock for the free product
                item.free_product.stock_length -= item.length * item.quantity
                item.free_product.save()

        return order



class VerifyPaymentView(APIView):
    def post(self, request, razorpay_order_id):
        """Verify Razorpay Payment with order_id in URL without signature verification."""

        # Fetch the order using the Razorpay order ID from the URL
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        # If order is already marked as paid, return a message
        if order.payment_status == "Paid":
            return Response({"message": "Payment already verified.", "price": str(order.total_price)}, status=status.HTTP_200_OK)

        # Update order status
        order.payment_status = "Paid"
        order.save()

        # Clear the cart after payment verification
        cart = Cart.objects.filter(user=order.user).first()
        if cart:
            cart.items.all().delete()

        # Return response with order ID, message, and total price
        return Response({
            "message": "Payment verified successfully.",
            "order_id": order.id,
            "price": str(order.total_price)
        }, status=status.HTTP_200_OK)



class SelectAddressView(ListAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return all addresses for the logged-in user
        return Address.objects.filter(user=self.request.user)