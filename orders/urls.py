from django.urls import path
from .views import ActiveAndPastOrdersView, DashboardView,DirectOrderView, ListOrdersView, CheckoutView,OrderUpdateView,ReturnOrderListView,PaymentDetailsListView,OrderDetailView,AdminOrderCreateView,\
            AdminOrderListAPIView,AdminOrderUpdateAPIView, ValidateStockAndOfferView,OrderAnalyticsView,BulkOrderUpdateView,BulkAdminOrderUpdateView,AdminUserOrderListView,ProcessReturnView,ReturnProductsView,\
            AdminOrderProcessReturnView,AdminOrderReturnProductsView
urlpatterns = [
    path('', ListOrdersView.as_view(), name='list-order'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order-detail'),  # Retrieve, update, or delete a specific order
    path('direct-order/', DirectOrderView.as_view(), name='direct-order'),  # Direct order placement
    path('checkout/', CheckoutView.as_view(), name='checkout'),  # Checkout view for address and payment option
    path('orders/<int:pk>/update/', OrderUpdateView.as_view(), name='order-update'),  # ORDER UPDATE NEW
    path('orders/returns/', ReturnOrderListView.as_view(), name='return-orders'), #GET RETURN PRODUCTS
    path('orders/payment-details/', PaymentDetailsListView.as_view(), name='payment-details'), #PAYMENT DETAILS
    path('admin/orders/', AdminOrderCreateView.as_view(), name='admin-order-create'),
    path('admin-orders/list/', AdminOrderListAPIView.as_view(), name='admin-order-list'),
    path('admin-orders/<int:pk>/', AdminOrderUpdateAPIView.as_view(), name='admin-order-update'),
    path('validate-stock-offer/', ValidateStockAndOfferView.as_view(), name='validate-stock-offer'),
    path('orders/active-past/', ActiveAndPastOrdersView.as_view(), name='active_and_past_orders'),
    path('order-analytics/', OrderAnalyticsView.as_view(), name='order-analytics'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('bulk-update/', BulkOrderUpdateView.as_view(), name="bulk-order-update"),
    path('admin-orders/bulk-update/', BulkAdminOrderUpdateView.as_view(), name='bulk_admin_order_update'),
    path('user-list/admin/', AdminUserOrderListView.as_view(), name='admin-order-user-list'),
    path('<int:order_id>/returns/', ProcessReturnView.as_view(), name='process-return'),
    path('returns/', ReturnProductsView.as_view(), name='return-products'),
    path('admin-orders/<int:admin_order_id>/process-return/', AdminOrderProcessReturnView.as_view(), name='admin-order-process-return'),
    path('admin-orders/returns/', AdminOrderReturnProductsView.as_view(), name='admin-order-returns'),

]
