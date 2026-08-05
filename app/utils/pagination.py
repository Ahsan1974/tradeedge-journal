"""Simple offset pagination helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass
class Page:
    items: list
    page: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        if self.per_page <= 0:
            return 0
        return max(1, ceil(self.total / self.per_page))

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def prev_page(self) -> int | None:
        return self.page - 1 if self.has_prev else None

    @property
    def next_page(self) -> int | None:
        return self.page + 1 if self.has_next else None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


def paginate(items: list, page: int = 1, per_page: int = 25) -> Page:
    page = max(1, page)
    per_page = max(1, min(per_page, 200))
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    return Page(items=items[start:end], page=page, per_page=per_page, total=total)


def clamp_page(page: int | None, default: int = 1) -> int:
    try:
        return max(1, int(page or default))
    except (TypeError, ValueError):
        return default
