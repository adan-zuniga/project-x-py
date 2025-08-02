"""Authentication and token management for ProjectX client."""

import base64
import datetime
import json
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

import pytz

from project_x_py.exceptions import ProjectXAuthenticationError
from project_x_py.models import Account

if TYPE_CHECKING:
    from project_x_py.client.protocols import ProjectXClientProtocol

logger = logging.getLogger(__name__)


class AuthenticationMixin:
    """Mixin class providing authentication functionality."""

    def __init__(self) -> None:
        """Initialize authentication attributes."""
        super().__init__()
        self.session_token = ""
        self.token_expiry: datetime.datetime | None = None
        self._authenticated = False
        self.account_info: Account | None = None

    async def _refresh_authentication(self: "ProjectXClientProtocol") -> None:
        """Refresh authentication if token is expired or about to expire."""
        if self._should_refresh_token():
            await self.authenticate()

    def _should_refresh_token(self: "ProjectXClientProtocol") -> bool:
        """Check if token should be refreshed."""
        if not self.token_expiry:
            return True

        # Refresh if token expires in less than 5 minutes
        buffer_time = timedelta(minutes=5)
        return datetime.datetime.now(pytz.UTC) >= (self.token_expiry - buffer_time)

    async def authenticate(self: "ProjectXClientProtocol") -> None:
        """
        Authenticate with ProjectX API and select account.

        This method handles the complete authentication flow:
        1. Authenticates with username and API key
        2. Retrieves available accounts
        3. Selects the specified account or first available

        The authentication token is automatically refreshed when needed
        during API calls.

        Raises:
            ProjectXAuthenticationError: If authentication fails
            ValueError: If specified account is not found

        Example:
            >>> async with AsyncProjectX.from_env() as client:
            >>>     await client.authenticate()
            >>>     print(f"Authenticated as {client.account_info.username}")
            >>>     print(f"Using account: {client.account_info.name}")
        """
        # Authenticate and get token
        auth_data = {
            "userName": self.username,
            "apiKey": self.api_key,
        }

        response = await self._make_request("POST", "/Auth/loginKey", data=auth_data)

        if not response:
            raise ProjectXAuthenticationError("Authentication failed")

        self.session_token = response["token"]
        self.headers["Authorization"] = f"Bearer {self.session_token}"

        # Parse token to get expiry
        try:
            token_parts = self.session_token.split(".")
            if len(token_parts) >= 2:
                # Add padding if necessary
                token_payload = token_parts[1]
                token_payload += "=" * (4 - len(token_payload) % 4)
                decoded = base64.urlsafe_b64decode(token_payload)
                token_data = json.loads(decoded)
                self.token_expiry = datetime.datetime.fromtimestamp(
                    token_data["exp"], tz=pytz.UTC
                )
        except Exception as e:
            self.logger.warning(f"Could not parse token expiry: {e}")
            # Set a default expiry of 1 hour
            self.token_expiry = datetime.datetime.now(pytz.UTC) + timedelta(hours=1)

        # Get accounts using the same endpoint as sync client
        payload = {"onlyActiveAccounts": True}
        accounts_response = await self._make_request(
            "POST", "/Account/search", data=payload
        )
        if not accounts_response or not accounts_response.get("success", False):
            raise ProjectXAuthenticationError("Account search failed")

        accounts_data = accounts_response.get("accounts", [])
        accounts = [Account(**acc) for acc in accounts_data]

        if not accounts:
            raise ProjectXAuthenticationError("No accounts found for user")

        # Select account
        if self.account_name:
            # Find specific account
            selected_account = None
            for account in accounts:
                if account.name.upper() == self.account_name.upper():
                    selected_account = account
                    break

            if not selected_account:
                available = ", ".join(acc.name for acc in accounts)
                raise ValueError(
                    f"Account '{self.account_name}' not found. "
                    f"Available accounts: {available}"
                )
        else:
            # Use first account
            selected_account = accounts[0]

        self.account_info = selected_account
        self._authenticated = True
        self.logger.info(
            f"Authenticated successfully. Using account: {selected_account.name}"
        )

    async def _ensure_authenticated(self: "ProjectXClientProtocol") -> None:
        """Ensure client is authenticated before making API calls."""
        if not self._authenticated or self._should_refresh_token():
            await self.authenticate()

    async def list_accounts(self: "ProjectXClientProtocol") -> list[Account]:
        """
        List all accounts available to the authenticated user.

        Returns:
            List of Account objects

        Raises:
            ProjectXError: If account listing fails

        Example:
            >>> accounts = await client.list_accounts()
            >>> for account in accounts:
            >>>     print(f"{account.name}: ${account.balance:,.2f}")
        """
        await self._ensure_authenticated()

        payload = {"onlyActiveAccounts": True}
        response = await self._make_request("POST", "/Account/search", data=payload)

        if not response or not response.get("success", False):
            return []

        accounts_data = response.get("accounts", [])
        return [Account(**acc) for acc in accounts_data]
