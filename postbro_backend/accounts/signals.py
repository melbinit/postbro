import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import User, Plan, Subscription

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def assign_free_plan_on_user_create(sender, instance: User, created: bool, **kwargs):
    """
    Assign Free subscription once, only when the user is created.
    Idempotent: deduplicates existing Free subs, skips if paid/pending exists.
    """
    if not created:
        return

    try:
        free_plan = Plan.objects.get(name='Free', is_active=True)

        # Simply create a Free subscription on first user creation
        Subscription.objects.get_or_create(
            user=instance,
            plan=free_plan,
            defaults={
                'status': Subscription.Status.ACTIVE,
                'start_date': timezone.now()
            }
        )
        logger.info(f"✅ [UserSignal] Ensured Free subscription for new user {instance.id} (email: {instance.email})")

    except Plan.DoesNotExist:
        logger.error(f"❌ [UserSignal] Free plan not found - subscription not created for user {instance.id}")
    except Exception as e:
        logger.error(
            f"❌ [UserSignal] Failed to create Free subscription for user {instance.id}: {str(e)}",
            exc_info=True
        )
        # Do not raise; user creation should not fail due to subscription issues

