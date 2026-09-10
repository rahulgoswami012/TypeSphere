TypeSphere Capability-Based Access Control Architecture.
Cleanly separates Guest experiences from Registered Pilot capabilities
without exposing future subscription or billing structures.
"""
from typing import Dict, Any
from flask_login import current_user

class PilotCapabilities:
    GUEST_CAPABILITIES = {
        'can_take_benchmark': True,
        'can_take_custom_test': True,
        'can_practice_academy': True,
        'can_play_arcade_solo': True,
        'can_view_leaderboards': True,
        'can_view_public_profiles': True,
        'can_submit_inquiry': True,
        'can_save_cloud_profile': False,
        'can_earn_certificates': False,
        'can_join_ranked_multiplayer': False,
        'can_record_personal_bests': False,
        'can_access_ai_telemetry': False,
        'can_race_personal_ghost': False,
        'can_persist_settings_profile': False,
        'can_submit_reviews': False,
    }

    REGISTERED_PILOT_CAPABILITIES = {
        'can_take_benchmark': True,
        'can_take_custom_test': True,
        'can_practice_academy': True,
        'can_play_arcade_solo': True,
        'can_view_leaderboards': True,
        'can_view_public_profiles': True,
        'can_submit_inquiry': True,
        'can_save_cloud_profile': True,
        'can_earn_certificates': True,
        'can_join_ranked_multiplayer': True,
        'can_record_personal_bests': True,
        'can_access_ai_telemetry': True,
        'can_race_personal_ghost': True,
        'can_persist_settings_profile': True,
        'can_submit_reviews': True,
    }

    @classmethod
    def get_capabilities(cls, user=None) -> Dict[str, bool]:
        target_user = user if user is not None else current_user
        if target_user and target_user.is_authenticated:
            return cls.REGISTERED_PILOT_CAPABILITIES.copy()
        return cls.GUEST_CAPABILITIES.copy()

    @classmethod
    def can(cls, capability_name: str, user=None) -> bool:
        caps = cls.get_capabilities(user)
        return caps.get(capability_name, False)

def inject_capabilities():
    """Context processor helper providing `pilot_can(capability)` across all Jinja templates."""
    return dict(
        pilot_can=PilotCapabilities.can,
        is_registered_pilot=current_user.is_authenticated if current_user else False,
        current_pilot=current_user if (current_user and current_user.is_authenticated) else None
    )