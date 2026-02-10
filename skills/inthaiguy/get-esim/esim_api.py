"""
API client for esimqr.link eSIM procurement.
Handles package search, quotes, and x402 purchase flow.
"""

import requests
from dataclasses import dataclass
from typing import Optional, List

BASE_URL = "https://esimqr.link"


@dataclass
class Package:
    """eSIM package details."""
    code: str
    name: str
    data: str
    duration: str
    country: str
    price_usd: Optional[float] = None


@dataclass
class Quote:
    """Price quote for a package."""
    package_code: str
    price_usdc: float
    price_raw: int  # Amount in smallest units


@dataclass
class PaymentRequired:
    """402 Payment Required response details."""
    nonce: str
    amount_raw: int
    amount_usdc: float
    pay_to: str
    asset: str
    network: str


@dataclass
class PurchaseResult:
    """Successful purchase result."""
    esim_id: str
    iccid: str
    activation_code: str
    esim_page_url: str  # User-friendly page with QR code and install instructions
    status_url: str


class ESIMApiError(Exception):
    """API error with status code."""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ESIMApi:
    """Client for esimqr.link API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ESIMAgent/1.0",
            "Accept": "application/json",
        })

    def search_packages(self, country: str) -> List[Package]:
        """
        Search for eSIM packages by country.

        Args:
            country: Country name or code (e.g., "US", "USA", "United States")

        Returns:
            List of available packages
        """
        url = f"{BASE_URL}/api/web3/packages"
        response = self.session.get(url, params={"q": country})

        if response.status_code != 200:
            raise ESIMApiError(
                f"Failed to search packages: {response.text}",
                status_code=response.status_code
            )

        data = response.json()
        packages = []

        for pkg in data.get("packages", data if isinstance(data, list) else []):
            packages.append(Package(
                code=pkg.get("packageCode", pkg.get("code", "")),
                name=pkg.get("name", ""),
                data=pkg.get("data", pkg.get("dataAmount", "")),
                duration=pkg.get("duration", pkg.get("validity", "")),
                country=pkg.get("country", country),
                price_usd=pkg.get("price", pkg.get("priceUsd")),
            ))

        return packages

    def get_quote(self, package_code: str) -> Quote:
        """
        Get price quote for a package.

        Args:
            package_code: Package code (e.g., "US_1_7")

        Returns:
            Quote with price details
        """
        url = f"{BASE_URL}/api/agent/quote"
        response = self.session.get(url, params={"packageCode": package_code})

        if response.status_code != 200:
            raise ESIMApiError(
                f"Failed to get quote: {response.text}",
                status_code=response.status_code
            )

        data = response.json()

        # Handle different response formats
        # The API returns usdcAmount as a string like "1.18"
        usdc_amount = data.get("usdcAmount", data.get("priceUsdc", data.get("price", "0")))
        if isinstance(usdc_amount, str):
            price_usdc = float(usdc_amount)
        else:
            price_usdc = float(usdc_amount)

        # Calculate raw amount (multiply by 10^6 for USDC decimals)
        price_raw = int(price_usdc * 1_000_000)

        return Quote(
            package_code=data.get("packageCode", package_code),  # Use internal code if provided
            price_usdc=price_usdc,
            price_raw=price_raw,
        )

    def initiate_purchase(self, package_code: str) -> PaymentRequired:
        """
        Initiate purchase - expects 402 Payment Required response.

        Args:
            package_code: Package code to purchase

        Returns:
            PaymentRequired with payment details
        """
        url = f"{BASE_URL}/api/agent/purchase"
        response = self.session.post(url, json={"packageCode": package_code})

        if response.status_code != 402:
            if response.status_code == 200:
                # Might be free or already paid
                raise ESIMApiError(
                    "Unexpected success - expected 402",
                    status_code=200,
                    response=response.json()
                )
            raise ESIMApiError(
                f"Unexpected response: {response.text}",
                status_code=response.status_code
            )

        data = response.json()

        # Parse x402 response - find the "transfer" scheme
        # The API returns multiple schemes: "exact" (gasless EIP-3009) and "transfer"
        # This implementation uses "transfer" - modify to use "exact" if your wallet supports EIP-3009
        accepts_list = data.get("accepts", [])
        accepts = None
        for scheme in accepts_list:
            if scheme.get("scheme") == "transfer":
                accepts = scheme
                break

        # Fallback to first scheme if transfer not found
        if accepts is None:
            accepts = accepts_list[0] if accepts_list else {}

        extra = accepts.get("extra", {})

        amount_raw = accepts.get("amount", 0)
        if isinstance(amount_raw, str):
            amount_raw = int(amount_raw)

        return PaymentRequired(
            nonce=extra.get("nonce", ""),
            amount_raw=amount_raw,
            amount_usdc=amount_raw / 1_000_000,
            pay_to=accepts.get("payTo", ""),
            asset=accepts.get("asset", ""),
            network=accepts.get("network", ""),
        )

    def complete_purchase(self, package_code: str, tx_hash: str, nonce: str) -> PurchaseResult:
        """
        Complete purchase with payment proof.

        Args:
            package_code: Package code being purchased
            tx_hash: Transaction hash of USDC payment
            nonce: Nonce from 402 response

        Returns:
            PurchaseResult with eSIM details
        """
        url = f"{BASE_URL}/api/agent/purchase"

        # Ensure tx_hash has 0x prefix
        if not tx_hash.startswith("0x"):
            tx_hash = f"0x{tx_hash}"

        headers = {
            "X-PAYMENT": f"txHash={tx_hash},nonce={nonce}"
        }

        response = self.session.post(
            url,
            json={"packageCode": package_code},
            headers=headers
        )

        if response.status_code != 200:
            raise ESIMApiError(
                f"Purchase failed: {response.text}",
                status_code=response.status_code,
                response=response.json() if response.text else None
            )

        data = response.json()

        esim_id = data.get("esimId", "")
        esim_details = data.get("esimDetails", {})

        return PurchaseResult(
            esim_id=esim_id,
            iccid=esim_details.get("iccid", ""),
            activation_code=esim_details.get("activationCode", ""),
            esim_page_url=data.get("esimPageUrl", f"{BASE_URL}/web3/esim/{esim_id}"),
            status_url=data.get("statusUrl", f"{BASE_URL}/api/agent/esim/{esim_id}"),
        )

    def get_esim_status(self, esim_id: str) -> dict:
        """
        Get status of an eSIM.

        Args:
            esim_id: eSIM ID from purchase

        Returns:
            Status dictionary
        """
        url = f"{BASE_URL}/api/agent/esim/{esim_id}"
        response = self.session.get(url)

        if response.status_code != 200:
            raise ESIMApiError(
                f"Failed to get eSIM status: {response.text}",
                status_code=response.status_code
            )

        return response.json()


if __name__ == "__main__":
    import sys

    api = ESIMApi()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python esim_api.py search <country>  - Search packages")
        print("  python esim_api.py quote <code>      - Get price quote")
        sys.exit(1)

    command = sys.argv[1]

    if command == "search" and len(sys.argv) > 2:
        country = " ".join(sys.argv[2:])
        print(f"Searching packages for: {country}")
        packages = api.search_packages(country)
        for pkg in packages:
            price_str = f"${pkg.price_usd:.2f}" if pkg.price_usd else "Quote required"
            print(f"  {pkg.code}: {pkg.name} - {pkg.data} / {pkg.duration} - {price_str}")

    elif command == "quote" and len(sys.argv) > 2:
        code = sys.argv[2]
        print(f"Getting quote for: {code}")
        quote = api.get_quote(code)
        print(f"  Price: ${quote.price_usdc:.2f} USDC")
        print(f"  Raw amount: {quote.price_raw}")

    else:
        print(f"Unknown command: {command}")
