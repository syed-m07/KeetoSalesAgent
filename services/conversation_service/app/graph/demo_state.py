"""
Demo State Definition for Guided Demonstrations.
Tracks the current step and status of a product demo workflow.
"""
from typing import TypedDict, Optional


class DemoState(TypedDict, total=False):
    """
    State for tracking guided demo progress.
    
    Attributes:
        is_active: Whether a demo session is currently running.
        step: Current step in the demo (0=Intro, 1=Search, 2=Select, 3=Control, 4=Complete).
        target_site: The site being demoed (e.g., "youtube").
        awaiting_confirmation: Whether we're waiting for user to say "yes" to proceed.
    """
    is_active: bool
    step: int
    target_site: str
    awaiting_confirmation: bool
