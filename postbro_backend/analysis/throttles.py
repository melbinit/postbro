from rest_framework.throttling import UserRateThrottle


class AnalyzeThrottle(UserRateThrottle):
    """
    Throttle analysis requests to 20 per hour per user
    """
    scope = 'analyze'
    rate = '20/hour'


class ChatThrottle(UserRateThrottle):
    """
    Throttle chat messages to 100 per hour per user
    """
    scope = 'chat'
    rate = '100/hour'

