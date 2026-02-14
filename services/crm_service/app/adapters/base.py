"""
Abstract Base Adapter for CRM providers.
All CRM integrations (HubSpot, Salesforce, etc.) must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Optional


class CRMClient(ABC):
    """
    Abstract CRM Client interface.
    
    Every CRM adapter must implement these methods so the main service
    can swap providers without changing any business logic.
    """

    @abstractmethod
    def create_contact(self, data: dict) -> dict:
        """
        Create a contact/lead in the external CRM.

        Args:
            data: Dict with keys: name, email, phone, company, summary.

        Returns:
            Dict with at minimum: {"external_id": "...", "provider": "..."}
        
        Raises:
            Exception on failure.
        """
        ...

    @abstractmethod
    def search_contact(self, email: str) -> Optional[dict]:
        """
        Search for an existing contact by email.

        Args:
            email: The email to search for.

        Returns:
            Dict with contact data if found, None otherwise.
        """
        ...

    @abstractmethod
    def update_contact(self, external_id: str, data: dict) -> dict:
        """
        Update an existing contact in the external CRM.

        Args:
            external_id: The ID of the contact in the external CRM.
            data: Dict of fields to update.

        Returns:
            Dict with updated contact data.
        """
        ...
