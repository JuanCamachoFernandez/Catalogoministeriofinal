from flask import request

from ..extensions import db


def paginate(query, serializer, default_per_page=20, max_per_page=100):
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = max(
            1, min(max_per_page, int(request.args.get("per_page", default_per_page)))
        )
    except (TypeError, ValueError):
        page, per_page = 1, default_per_page
    result = db.paginate(query, page=page, per_page=per_page, error_out=False)
    return {
        "items": [serializer(item) for item in result.items],
        "pagination": {
            "page": result.page,
            "per_page": result.per_page,
            "pages": result.pages,
            "total": result.total,
            "has_next": result.has_next,
            "has_prev": result.has_prev,
        },
    }
