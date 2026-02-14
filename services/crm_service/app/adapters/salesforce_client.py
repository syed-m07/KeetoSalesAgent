"""
Salesforce CRM Adapter.
Uses the 'simple-salesforce' library with Username-Password OAuth flow.
Free Developer Edition: 5,000 API calls/24h.
"""
import os
import logging
from typing import Optional

from simple_salesforce import Salesforce, SalesforceResourceNotFound

from .base import CRMClient

logger = logging.getLogger(__name__)


class SalesforceAdapter(CRMClient):
    """
    Salesforce CRM adapter using Username-Password authentication.
    
    Requires env vars:
      SALESFORCE_USERNAME
      SALESFORCE_PASSWORD
      SALESFORCE_SECURITY_TOKEN
    """

    def __init__(self):
        username = os.getenv("SALESFORCE_USERNAME")
        password = os.getenv("SALESFORCE_PASSWORD")
        security_token = os.getenv("SALESFORCE_SECURITY_TOKEN")

        if not all([username, password, security_token]):
            raise ValueError(
                "Salesforce credentials not fully set. "
                "Need: SALESFORCE_USERNAME, SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN"
            )

        try:
            self.sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
            )
            logger.info("✅ Salesforce adapter initialized")
        except Exception as e:
            logger.error(f"❌ Salesforce auth failed: {e}")
            raise

    def create_contact(self, data: dict) -> dict:
        """
        Create a Lead in Salesforce.
        
        Maps local Lead fields to Salesforce Lead object:
          name -> FirstName + LastName
          email -> Email
          phone -> Phone
          company -> Company (REQUIRED by Salesforce)
          summary -> Description
        """
        name_parts = data.get("name", "Unknown").split(" ", 1)
        firstname = name_parts[0]
        lastname = name_parts[1] if len(name_parts) > 1 else firstname

        sf_data = {
            "FirstName": firstname,
            "LastName": lastname,
            "Email": data.get("email", ""),
            "Phone": data.get("phone", ""),
            "Company": data.get("company", "Unknown Company"),  # Required field
            "Description": data.get("summary", ""),
            "LeadSource": "AI Sales Agent",
        }

        # Remove empty values (but keep Company)
        sf_data = {k: v for k, v in sf_data.items() if v or k == "Company"}

        try:
            result = self.sf.Lead.create(sf_data)
            external_id = result.get("id")
            logger.info(f"✅ Salesforce lead created: {external_id}")
            return {
                "external_id": external_id,
                "provider": "salesforce",
            }
        except Exception as e:
            logger.error(f"❌ Salesforce create error: {e}")
            raise

    def search_contact(self, email: str) -> Optional[dict]:
        """Search for a Lead in Salesforce by email using SOQL."""
        if not email:
            return None

        try:
            query = f"SELECT Id, FirstName, LastName, Email, Company FROM Lead WHERE Email = '{email}' LIMIT 1"
            results = self.sf.query(query)

            if results.get("totalSize", 0) > 0:
                record = results["records"][0]
                return {
                    "external_id": record["Id"],
                    "provider": "salesforce",
                    "properties": {
                        "firstname": record.get("FirstName", ""),
                        "lastname": record.get("LastName", ""),
                        "email": record.get("Email", ""),
                        "company": record.get("Company", ""),
                    },
                }
            return None
        except Exception as e:
            logger.error(f"❌ Salesforce search error: {e}")
            return None

    def update_contact(self, external_id: str, data: dict) -> dict:
        """Update an existing Lead in Salesforce."""
        sf_update = {}
        if "name" in data:
            name_parts = data["name"].split(" ", 1)
            sf_update["FirstName"] = name_parts[0]
            if len(name_parts) > 1:
                sf_update["LastName"] = name_parts[1]
        if "email" in data:
            sf_update["Email"] = data["email"]
        if "phone" in data:
            sf_update["Phone"] = data["phone"]
        if "company" in data:
            sf_update["Company"] = data["company"]

        try:
            self.sf.Lead.update(external_id, sf_update)
            logger.info(f"✅ Salesforce lead updated: {external_id}")
            return {
                "external_id": external_id,
                "provider": "salesforce",
            }
        except SalesforceResourceNotFound:
            logger.error(f"❌ Salesforce lead not found: {external_id}")
            raise
        except Exception as e:
            logger.error(f"❌ Salesforce update error: {e}")
            raise
