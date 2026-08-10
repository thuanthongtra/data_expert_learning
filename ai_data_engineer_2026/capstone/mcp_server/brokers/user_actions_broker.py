from __future__ import annotations

from real_estate_app.repositories import area_repository


def save_research_note(user_id: str, title: str, note_text: str, related_area_slug: str | None = None) -> dict:
    return area_repository.save_research_note(user_id, title, note_text, related_area_slug)


def create_comparison_report(user_id: str, area_slug_a: str, area_slug_b: str, prompt: str, report_text: str) -> dict:
    return area_repository.create_comparison_report(user_id, area_slug_a, area_slug_b, prompt, report_text)


def save_area(user_id: str, area_slug: str) -> dict:
    inserted = area_repository.save_area(user_id, area_slug)
    return {"user_id": user_id, "area_slug": area_slug, "inserted": bool(inserted)}
