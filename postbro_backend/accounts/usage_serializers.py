"""
Serializers for usage tracking
"""
from rest_framework import serializers
from .models import UserUsage, Plan, Subscription


class UsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserUsage
        fields = [
            'id', 'platform', 'date',
            'handle_analyses', 'url_lookups', 'post_suggestions', 'questions_asked',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PlanLimitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'max_handles', 'max_urls', 'max_analyses_per_day', 'max_questions_per_day'
        ]


class UsageSummarySerializer(serializers.Serializer):
    """Serializer for usage summary response"""
    plan = PlanLimitsSerializer()
    usage = serializers.DictField()
    date = serializers.DateField()
    
    def to_representation(self, instance):
        # Custom representation for usage summary
        return instance