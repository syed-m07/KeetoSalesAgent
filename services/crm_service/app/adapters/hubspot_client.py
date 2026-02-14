"""
HubSpot CRM Adapter.
Uses the HubSpot API v3 via the official 'hubspot-api-client' package.
Free tier: 250,000 API calls/day.
"""
import os
import logging
from typing import Optional

from hubspot import HubSpot
from hubspot.crm.contacts import (
    SimplePublicObjectInputForCreate,
    PublicObjectSearchRequest,
    FilterGroup,
    Filter,
)
from hubspot.crm.contacts.exceptions import ApiException

from .base import CRMClient

logger = logging.getLogger(__name__)


class HubSpotAdapter(CRMClient):
    """
    HubSpot CRM adapter using Private App access token.
    
    Requires env var: HUBSPOT_ACCESS_TOKEN
    """

    def __init__(self):
        token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        if not token:
            raise ValueError("HUBSPOT_ACCESS_TOKEN environment variable is not set")
        self.client = HubSpot(access_token=token)
        logger.info("✅ HubSpot adapter initialized")

    def create_contact(self, data: dict) -> dict:
        """
        Create a contact in HubSpot.
        
        Maps local Lead fields to HubSpot Contact properties:
          name -> firstname + lastname
          email -> email
          phone -> phone
          company -> company
          summary -> description (hs_lead_status note)
        """
        # Split name into first/last
        name_parts = data.get("name", "Unknown").split(" ", 1)
        firstname = name_parts[0]
        lastname = name_parts[1] if len(name_parts) > 1 else ""

        properties = {
            "firstname": firstname,
            "lastname": lastname,
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "company": data.get("company", ""),
            # Use the 'message' property or a custom note for the summary
            "hs_lead_status": "NEW",
        }

        # Remove empty values to avoid API errors
        properties = {k: v for k, v in properties.items() if v}

        try:
            contact_input = SimplePublicObjectInputForCreate(properties=properties)
            response = self.client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=contact_input
            )
            
            external_id = response.id
            logger.info(f"✅ HubSpot contact created: {external_id}")
            
            return {
                "external_id": str(external_id),
                "provider": "hubspot",
                "properties": response.properties,
            }

        except ApiException as e:
            # Handle duplicate contact (409 Conflict)
            if e.status == 409:
                logger.warning(f"⚠️ HubSpot contact already exists for {data.get('email')}")
                # Try to find existing contact
                existing = self.search_contact(data.get("email", ""))
                if existing:
                    return existing
            logger.error(f"❌ HubSpot API error: {e}")
            raise

    def search_contact(self, email: str) -> Optional[dict]:
        """Search for a contact in HubSpot by email."""
        if not email:
            return None

        try:
            filter = Filter(
                property_name="email",
                operator="EQ",
                value=email,
            )
            filter_group = FilterGroup(filters=[filter])
            search_request = PublicObjectSearchRequest(
                filter_groups=[filter_group],
                limit=1,
            )

            response = self.client.crm.contacts.search_api.do_search(
                public_object_search_request=search_request
            )

            if response.total > 0:
                contact = response.results[0]
                return {
                    "external_id": str(contact.id),
                    "provider": "hubspot",
                    "properties": contact.properties,
                }
            return None

        except ApiException as e:
            logger.error(f"❌ HubSpot search error: {e}")
            return None

    def update_contact(self, external_id: str, data: dict) -> dict:
        """Update an existing contact in HubSpot."""
        from hubspot.crm.contacts import SimplePublicObjectInput

        properties = {}
        if "name" in data:
            name_parts = data["name"].split(" ", 1)
            properties["firstname"] = name_parts[0]
            if len(name_parts) > 1:
                properties["lastname"] = name_parts[1]
        if "email" in data:
            properties["email"] = data["email"]
        if "phone" in data:
            properties["phone"] = data["phone"]
        if "company" in data:
            properties["company"] = data["company"]

        try:
            update_input = SimplePublicObjectInput(properties=properties)
            response = self.client.crm.contacts.basic_api.update(
                contact_id=external_id,
                simple_public_object_input=update_input,
            )
            logger.info(f"✅ HubSpot contact updated: {external_id}")
            return {
                "external_id": str(response.id),
                "provider": "hubspot",
                "properties": response.properties,
            }
        except ApiException as e:
            logger.error(f"❌ HubSpot update error: {e}")
            raise
