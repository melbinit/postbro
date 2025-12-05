from rest_framework import serializers
from .models import User, Plan, Subscription
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    full_name = serializers.CharField(required=False, allow_blank=True)
    company_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name', 'company_name')

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            company_name=validated_data.get('company_name', ''),
            is_active=False,  # Inactive until email verified
            email_verified=False
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                              email=email, password=password)

            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')

            if not user.is_active:
                msg = _('User account is disabled.')
                raise serializers.ValidationError(msg, code='authorization')

            if not user.email_verified:
                msg = _('Please verify your email before logging in.')
                raise serializers.ValidationError(msg, code='authorization')

        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('No user found with this email address.')
        return value

class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    def validate(self, attrs):
        # Check if passwords match
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        
        # Validate password strength
        validate_password(attrs['password'])
        
        # Check if token is valid and not expired
        try:
            user = User.objects.get(
                email__iexact=attrs['email'],
                password_reset_token=attrs['token']
            )
            
            # Check if token is expired (24 hours)
            if user.password_reset_sent_at and (timezone.now() - user.password_reset_sent_at).total_seconds() > 86400:
                raise serializers.ValidationError({'token': 'Password reset link has expired.'})
            
            attrs['user'] = user
            return attrs
            
        except User.DoesNotExist:
            raise serializers.ValidationError({'token': 'Invalid or expired password reset link.'})

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'company_name', 'profile_image', 'created_at', 'updated_at')
        read_only_fields = ('id', 'email', 'created_at', 'updated_at')

    def validate_full_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Full name must be at least 2 characters long.')
        return value.strip()

    def validate_company_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError('Company name must be at least 2 characters long.')
        return value.strip() if value else value

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ('id', 'name', 'description', 'price', 'max_handles', 
                 'max_urls', 'max_analyses_per_day', 'max_questions_per_day', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')

class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Subscription
        fields = ('id', 'plan', 'plan_id', 'status', 'start_date', 
                 'end_date', 'created_at', 'updated_at')
        read_only_fields = ('id', 'status', 'start_date', 'end_date', 
                          'created_at', 'updated_at')

    def validate_plan_id(self, value):
        try:
            Plan.objects.get(id=value, is_active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError('Invalid or inactive plan selected.')
        return value

class SubscriptionCreateSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField(required=True)
    
    def validate_plan_id(self, value):
        try:
            plan = Plan.objects.get(id=value, is_active=True)
            if plan.price == 0:
                raise serializers.ValidationError('Free plan cannot be subscribed to directly.')
        except Plan.DoesNotExist:
            raise serializers.ValidationError('Invalid or inactive plan selected.')
        return value 