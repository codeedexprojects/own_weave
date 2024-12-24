from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView,CreateAPIView
from accounts.permissions import IsAdminOrStaff
from .models import CategorySize, Offer, Product, Category, SubCategory,Testimonial
from .serializers import CategorySizeSerializer, OfferSerializer, ProductSerializer, CategorySerializer, SubCategorySerializer,TestimonialSerializer
from rest_framework import generics
from rest_framework.views import APIView
from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated,IsAdminUser




# Admin views

class OfferViewSet(viewsets.ModelViewSet):
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    permission_classes = [IsAdminOrStaff]

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrStaff]

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAdminOrStaff]

class CategorySizeViewSet(viewsets.ModelViewSet):
    queryset = CategorySize.objects.all()
    serializer_class = CategorySizeSerializer
    permission_classes = [IsAdminOrStaff]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_visible_in_listing=True).order_by('-id','is_out_of_stock')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrStaff]

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        selected_length = request.query_params.get('length', None)

        serializer_context = {
            'selected_length': float(selected_length) if selected_length else 1
        }

        serializer = self.get_serializer(product, context=serializer_context)
        return Response(serializer.data)




# Customer views
class ProductListView(ListAPIView):
    queryset = Product.objects.filter(is_visible_in_listing=True).order_by('-id','is_out_of_stock')
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to view products

class CategoryListView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to view products


class ProductDetailView(RetrieveAPIView):
    queryset = Product.objects.filter(is_visible_in_listing=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to view product details


class ProductCategoryFilterView(ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to view products by category

    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        query = self.request.query_params.get('q', None)

        # Filter products by category and search by name or product code if query is provided
        queryset = Product.objects.filter(category_id=category_id,is_visible_in_listing=True).order_by('is_out_of_stock', '-id')
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(product_code__icontains=query))

        return queryset


class ProductSubCategoryFilterView(ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to view products by subcategory

    def get_queryset(self):
        subcategory_id = self.kwargs.get('subcategory_id')
        return Product.objects.filter(sub_category_id=subcategory_id,is_visible_in_listing=True)


class ProductSearchView(ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        query = self.request.query_params.get('q', None)
        if query:
            return Product.objects.filter(Q(name__icontains=query) | Q(product_code__icontains=query)).order_by('-id','is_out_of_stock')
        return Product.objects.none()


class ProductFilterByCategoryView(ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        Return products filtered by category ID or category name.
        """
        category_id = self.request.query_params.get('category_id')
        category_name = self.request.query_params.get('category_name')

        queryset = Product.objects.filter(is_visible_in_listing=True)

        # Filter by category ID
        if category_id:
            queryset = queryset.filter(category_id=category_id).order_by('-id','is_out_of_stock')

        # Filter by category name
        if category_name:
            queryset = queryset.filter(category__name__icontains=category_name).order_by('-id','is_out_of_stock')

        return queryset

class TestimonialViewSet(generics.ListCreateAPIView):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    permission_classes = []

class TestimonialDetailViewSet(generics.RetrieveUpdateDestroyAPIView):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    permission_classes = []

class ProductCountView(generics.ListAPIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request, *args, **kwargs):
        total_products = Product.objects.count()
        return Response({"total_products": total_products})


class LastUpdatedProductsView(ListAPIView):
    queryset = Product.objects.filter(is_visible_in_listing=True).order_by('-updated_at')[:5]
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]




