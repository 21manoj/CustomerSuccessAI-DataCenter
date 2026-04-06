from decimal import Decimal

from django.conf import settings


def _usd(amount: Decimal, currency: str) -> Decimal:
    """Rough static conversion for governance checks (MVP). Replace with live rates in production."""
    currency = (currency or "USD").upper()
    rates = getattr(settings, "MVP_EXCHANGE_RATES_TO_USD", {"USD": "1", "INR": "0.012"})
    rate = Decimal(str(rates.get(currency, "1")))
    return amount * rate


def need_requires_governance(target_amount: Decimal, currency: str) -> bool:
    usd = _usd(target_amount, currency)
    return usd >= Decimal(str(settings.GOVERNANCE_THRESHOLD_NEED_USD))


def project_requires_governance(budget: Decimal, currency: str) -> bool:
    usd = _usd(budget, currency)
    return usd >= Decimal(str(settings.GOVERNANCE_THRESHOLD_PROJECT_USD))


def expense_requires_governance(amount: Decimal, currency: str) -> bool:
    usd = _usd(amount, currency)
    return usd >= Decimal(str(settings.GOVERNANCE_THRESHOLD_EXPENSE_USD))
