import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from typing import Any
import httpx
from ..config import Settings
from ..database import DatabaseManager

logger = logging.getLogger(__name__)

SUPPORTED_CURRENCIES = ["USD", "EUR", "TRY", "RUB", "GEL"]

DEFAULT_FALLBACK_RATES: dict[str, Decimal] = {
    "USD": Decimal("1.700000"),
    "EUR": Decimal("1.850000"),
    "TRY": Decimal("0.049000"),
    "RUB": Decimal("0.017500"),
    "GEL": Decimal("0.620000")
}

class CurrencySyncService:
    def __init__(self, db: DatabaseManager, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def fetch_from_cbar(self) -> dict[str, Decimal] | None:
        today_str = datetime.now().strftime("%d.%m.%Y")
        url = self.settings.CBAR_URL.format(date=today_str) if "{date}" in self.settings.CBAR_URL else self.settings.CBAR_URL

        try:
            with httpx.Client(timeout=self.settings.CBAR_TIMEOUT) as client:
                response = client.get(url)
                if response.status_code != 200:
                    logger.warning("cbar.az returned status code %s for URL %s", response.status_code, url)
                    return None

                root = ET.fromstring(response.text)
                rates: dict[str, Decimal] = {}

                # Search through Valute elements
                for valute in root.findall(".//Valute"):
                    code = valute.get("Code")
                    if code and code.upper() in SUPPORTED_CURRENCIES:
                        val_elem = valute.find("Value")
                        nominal_elem = valute.find("Nominal")
                        if val_elem is not None and val_elem.text:
                            # Replace comma with period if needed
                            val_str = val_elem.text.strip().replace(",", ".")
                            nominal = Decimal(nominal_elem.text.strip()) if (nominal_elem is not None and nominal_elem.text) else Decimal("1")
                            rate_per_unit = Decimal(val_str) / nominal
                            rates[code.upper()] = round(rate_per_unit, 6)

                if rates:
                    return rates
                logger.warning("No supported currencies found in cbar.az XML response.")
                return None

        except Exception as exc:
            logger.warning("Failed to fetch rates from cbar.az: %s. Using cached rates.", exc)
            return None

    def sync(self) -> dict[str, Any]:
        rates = self.fetch_from_cbar()

        if rates:
            with self.db.get_connection() as (_, cursor):
                for code, rate in rates.items():
                    cursor.execute(
                        """
                        INSERT INTO currency_rates (currency_code, rate, source, fetched_at)
                        VALUES (%s, %s, 'cbar.az', NOW())
                        ON CONFLICT (currency_code, fetched_at)
                        DO UPDATE SET rate = EXCLUDED.rate;
                        """,
                        (code, rate)
                    )
            return {
                "rates": rates,
                "source": "cbar.az",
                "fetched_at": datetime.now().isoformat()
            }

        # Offline fallback
        return self._get_cached_rates_with_metadata()

    def _get_cached_rates_with_metadata(self) -> dict[str, Any]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT DISTINCT ON (currency_code) currency_code, rate, fetched_at
                FROM currency_rates
                ORDER BY currency_code, fetched_at DESC;
                """
            )
            rows = cursor.fetchall()

        if rows:
            cached_rates = {r["currency_code"]: Decimal(str(r["rate"])) for r in rows}
            latest_date = max(r["fetched_at"] for r in rows if r["fetched_at"])
            return {
                "rates": cached_rates,
                "source": "cache",
                "cached_at": latest_date.isoformat() if latest_date else datetime.now().isoformat()
            }

        return {
            "rates": DEFAULT_FALLBACK_RATES.copy(),
            "source": "cache",
            "cached_at": datetime.now().isoformat()
        }

    def get_latest_rates(self) -> dict[str, Any]:
        with self.db.get_connection() as (_, cursor):
            cursor.execute(
                """
                SELECT DISTINCT ON (currency_code) currency_code, rate, fetched_at, source
                FROM currency_rates
                ORDER BY currency_code, fetched_at DESC;
                """
            )
            rows = cursor.fetchall()

        if rows:
            rates = {r["currency_code"]: Decimal(str(r["rate"])) for r in rows}
            source = rows[0]["source"] if rows else "cache"
            latest_date = max(r["fetched_at"] for r in rows if r["fetched_at"])
            return {
                "rates": rates,
                "source": source,
                "fetched_at": latest_date.isoformat() if latest_date else None
            }

        return self.sync()

    def get_rate(self, currency_code: str) -> Decimal:
        code = currency_code.upper()
        if code == "AZN":
            return Decimal("1.000000")

        rates_info = self.get_latest_rates()
        rates = rates_info.get("rates", {})
        if code in rates:
            return Decimal(str(rates[code]))

        if code in DEFAULT_FALLBACK_RATES:
            return DEFAULT_FALLBACK_RATES[code]

        raise ValueError(f"Exchange rate for currency '{code}' is not available.")
