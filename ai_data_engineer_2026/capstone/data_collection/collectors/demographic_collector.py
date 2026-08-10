from __future__ import annotations

from data_collection.transformers.normalization import stable_id


class DemographicCollector:
    """Seed demographic summary rows until a full StatsCan pipeline is wired in."""

    def collect(self, neighbourhoods: list[dict]) -> list[dict]:
        rows = []
        for neighbourhood in neighbourhoods:
            slug = neighbourhood["slug"]
            for metric_name, metric_value, metric_unit in self._defaults_for_area(slug):
                rows.append(
                    {
                        "id": stable_id("demographic", slug, metric_name, "2026-01-01"),
                        "area_slug": slug,
                        "snapshot_date": "2026-01-01",
                        "metric_name": metric_name,
                        "metric_value": metric_value,
                        "metric_unit": metric_unit,
                        "source": "seed_placeholder",
                        "payload": {"note": "Placeholder seed row pending StatsCan/open data integration."},
                    }
                )
        return rows


    def _defaults_for_area(self, slug: str) -> list[tuple[str, float, str]]:
        base = [
            ("population_index", 100.0, "index"),
            ("median_household_income_index", 100.0, "index"),
            ("renter_share_index", 100.0, "index"),
            ("family_share_index", 100.0, "index"),
        ]
        adjustments = {
            "willowdale-east": [105.0, 112.0, 108.0, 95.0],
            "bayview-village": [96.0, 120.0, 92.0, 102.0],
            "don-mills": [103.0, 108.0, 97.0, 101.0],
            "clanton-park": [99.0, 102.0, 110.0, 94.0],
            "downsview": [110.0, 88.0, 111.0, 98.0],
        }
        values = adjustments.get(slug, [item[1] for item in base])
        return [(base[idx][0], values[idx], base[idx][2]) for idx in range(len(base))]


class SeedDemographicCollector(DemographicCollector):
    pass
