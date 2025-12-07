import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    username = None  # Disable username field
    
    # Clerk integration
    clerk_user_id = models.CharField(max_length=255, null=True, blank=True, unique=True, help_text='Clerk user ID')
    
    # Legacy Supabase field (kept for migration compatibility, can be removed later)
    supabase_user_id = models.UUIDField(null=True, blank=True, unique=True, help_text='Supabase auth.users ID (deprecated)')
    
    full_name = models.CharField(_('full name'), max_length=255, blank=True)
    company_name = models.CharField(_('company name'), max_length=255, blank=True)
    email_verified = models.BooleanField(_('email verified'), default=False)  # Synced from Clerk
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Profile
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    
    # Note: Password reset handled by Clerk - no need to store tokens

    # Fix reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='custom_user_set',
        related_query_name='custom_user',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    max_handles = models.PositiveIntegerField(default=1)
    max_urls = models.PositiveIntegerField(default=5)
    max_analyses_per_day = models.PositiveIntegerField(default=10)
    max_questions_per_day = models.PositiveIntegerField(
        default=10,
        help_text='Maximum chat questions per day'
    )
    # Payment provider product IDs (for linking to external payment systems)
    provider_product_id = models.CharField(
        max_length=255,
        blank=True,
        help_text='Payment provider Product ID (e.g., Dodo product_id or Stripe price_id)'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.name} (${self.price}/month)"

class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        PENDING = 'pending', _('Pending Payment')
        TRIAL = 'trial', _('Trial')
        FAILED = 'failed', _('Payment Failed')
        CANCELING = 'canceling', _('Canceling at Period End')
        CANCELLED = 'cancelled', _('Cancelled')
        EXPIRED = 'expired', _('Expired')
    
    class PaymentProvider(models.TextChoices):
        STRIPE = 'stripe', _('Stripe')
        DODO = 'dodo', _('Dodo Payments')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Payment provider fields
    payment_provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.DODO,
        help_text='Payment provider (stripe, dodo, etc.)'
    )
    provider_customer_id = models.CharField(
        max_length=255,
        blank=True,
        help_text='Payment provider Customer ID (e.g., Stripe cus_xxx or Dodo customer ID)'
    )
    provider_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        help_text='Payment provider Subscription ID (e.g., Stripe sub_xxx or Dodo subscription ID)'
    )
    downgrade_to_plan = models.ForeignKey(
        'Plan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_downgrades',
        help_text='Plan to downgrade to when current period ends (only set when status is CANCELING for downgrades)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_provider', 'provider_customer_id']),
            models.Index(fields=['payment_provider', 'provider_subscription_id']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status}) - {self.payment_provider}"

class UserUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usage')
    date = models.DateField()
    platform = models.CharField(max_length=50)  # e.g., 'twitter', 'instagram'
    handle_analyses = models.PositiveIntegerField(default=0)
    url_lookups = models.PositiveIntegerField(default=0)
    post_suggestions = models.PositiveIntegerField(default=0)
    questions_asked = models.PositiveIntegerField(
        default=0,
        help_text='Number of chat questions asked today'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'date', 'platform']
        ordering = ['-date', 'platform']

    def __str__(self):
        return f"{self.user.email} - {self.date} - {self.platform}"
