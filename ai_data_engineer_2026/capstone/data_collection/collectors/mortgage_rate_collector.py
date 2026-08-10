from __future__ import annotations

from data_collection.clients.bank_of_canada_client import BankOfCanadaClient
from data_collection.transformers.normalization import safe_float, stable_id


class MortgageRateCollector:
    def __init__(self):
        self.client = BankOfCanadaClient()

    def collect(self) -> list[dict]:
        rows = []
        for series_name in self.client.configured_series():
            try:
                observations = self.client.get_series_observations(series_name, recent=30)
            except Exception:
                continue
            for observation in observations:
                value = observation.get(series_name, {}).get("v")
                rate_value = safe_float(value)
                if rate_value is None:
                    continue
                rows.append(
                    {
                        "id": stable_id("mortgage_rate", series_name, observation.get("d")),
                        "series_name": series_name,
                        "observation_date": observation.get("d"),
                        "rate_value": rate_value,
                        "unit": "percent",
                        "source": "bank_of_canada_valet",
                        "payload": observation,
                    }
                )
        return rows
