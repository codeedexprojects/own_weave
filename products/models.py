from django.db import models
from datetime import timedelta
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.timezone import now

class Offer(models.Model):
    OFFER_TYPE_CHOICES = [
        ('BOGO', 'Buy 1 Get 1 Free'),
        ('PERCENTAGE', 'Percentage Discount'),
    ]

    name = models.CharField(max_length=255)  # Offer name
    offer_type = models.CharField(max_length=10, choices=OFFER_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # For percentage offers
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Time when the record is created
    updated_at = models.DateTimeField(auto_now=True)  # Time when the record is last updated

    def __str__(self):
        return f"{self.name} - {self.get_offer_type_display()}"


class Category(models.Model):
    name = models.CharField(max_length=255)
    heading = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    offer = models.ForeignKey('Offer', null=True, blank=True, on_delete=models.SET_NULL, related_name="categories")
    image = models.ImageField(upload_to='categories/images/', default=None)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Time when the record is created
    updated_at = models.DateTimeField(auto_now=True)  # Time when the record is last updated

    def __str__(self):
        return self.name


class CategorySize(models.Model):
    SIZE_CHOICES = [
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
        ('XXXL', 'Triple Extra Large'),
    ]

    SLEEVE_CHOICES = [
        ('full', 'Full Sleeve'),
        ('half', 'Half Sleeve'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="sizes")
    width = models.DecimalField(max_digits=5, decimal_places=2, help_text="Width in inches (e.g., 44, 60, 120)")

    # Define fields for each size and sleeve length within this width
    size_L_full_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_L_half_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XL_full_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XL_half_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XXL_full_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XXL_half_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XXXL_full_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XXXL_half_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Time when the record is created
    updated_at = models.DateTimeField(auto_now=True)  # Time when the record is last updated

    def __str__(self):
        return f"{self.category.name} - {self.width} inch width"

    def get_length(self, size, sleeve):
        # Construct the field name based on the size and sleeve
        field_name = f"size_{size}_{sleeve}_length"
        # Fetch and return the value of the corresponding field
        return getattr(self, field_name, None)



class SubCategory(models.Model):
    # Fields remain the same
    name = models.CharField(max_length=255)
    main_category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.CASCADE)
    # size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # image = models.ImageField(upload_to='subcategories/images/')
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255, null=False)
    product_code = models.CharField(max_length=100, unique=True, default=None, null=False)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE, null=False, default=None)
    sub_category = models.ForeignKey(SubCategory, null=True, blank=True, related_name='products', on_delete=models.CASCADE)
    width = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Width in inches")
    price_per_meter = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    offer_price_per_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    wholesale_price_per_meter = models.DecimalField(max_digits=10, decimal_places=2, null=False, help_text="Price per meter for wholesale purchase")
    offer = models.ForeignKey(Offer, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    stock_length = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False)
    gsm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_popular = models.BooleanField(default=False)
    is_offer_product = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    fabric = models.CharField(max_length=255, null=True, blank=True)
    pattern = models.CharField(max_length=255, null=True, blank=True)
    fabric_composition = models.CharField(max_length=255, null=True, blank=True)
    fit = models.CharField(max_length=255, null=True, blank=True)
    style = models.CharField(max_length=255, null=True, blank=True)
    color = models.CharField(max_length=255, null=True, blank=True)
    is_out_of_stock = models.BooleanField(default=False)
    out_of_stock_date = models.DateTimeField(null=True, blank=True)
    is_visible_in_listing = models.BooleanField(default=True)
    invested_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # Corrected the use of category_size and replaced with width
        return f"{self.name} - {self.width} inch width"

    def update_stock_status(self):
        """Update the stock status and visibility based on stock length."""
        if self.stock_length < 1.5 and not self.is_out_of_stock:
            self.is_out_of_stock = True
            self.out_of_stock_date = now()
            self.is_visible_in_listing = True  # Initially visible for 10 days
        elif self.is_out_of_stock:
            if self.out_of_stock_date and (now() - self.out_of_stock_date).days > 10:
                self.is_visible_in_listing = False  # Make invisible after 10 days
        else:
            self.is_out_of_stock = False
            self.is_visible_in_listing = True

    def save(self, *args, **kwargs):
        """Override save to always update stock status."""
        self.update_stock_status()
        super().save(*args, **kwargs)

    def available_lengths(self):
        """
        Return available lengths for the selected width (CategorySize).
        """
        category_size = self.category.sizes.filter(width=self.width).first()
        if category_size:
            return {
                "size_L_full_length": category_size.size_L_full_length,
                "size_L_half_length": category_size.size_L_half_length,
                "size_XL_full_length": category_size.size_XL_full_length,
                "size_XL_half_length": category_size.size_XL_half_length,
                "size_XXL_full_length": category_size.size_XXL_full_length,
                "size_XXL_half_length": category_size.size_XXL_half_length,
                "size_XXXL_full_length": category_size.size_XXXL_full_length,
                "size_XXXL_half_length": category_size.size_XXXL_half_length,
            }
        return {}

    def get_length(self, size, sleeve):
        """
        Get the specific length for a size and sleeve from CategorySize.
        """
        category_size = self.category.sizes.filter(width=self.width).first()
        if category_size:
            return category_size.get_length(size, sleeve)
        return None


@receiver(pre_save, sender=Product)
def calculate_invested_amount(sender, instance, **kwargs):
    """
    Calculate the invested amount before saving the Product instance.
    """
    if instance.stock_length and instance.wholesale_price_per_meter:
        instance.invested_amount = instance.stock_length * instance.wholesale_price_per_meter
    else:
        instance.invested_amount = 0  # Default to 0 if either field is missing

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/images/')

    def __str__(self):
        return f"Image for {self.product.name}"


class Testimonial(models.Model):
    thumbnail = models.ImageField(upload_to='testimonial_thumbnails/')
    youtube_link = models.URLField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)