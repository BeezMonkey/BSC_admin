VALID_DIRECTIONS = {"asc", "desc"}


def apply_sorting(request, queryset, allowed_sorts, default_sort=None, default_direction="asc"):
    requested_sort = request.GET.get("sort", "").strip()
    direction = request.GET.get("direction", default_direction).strip().lower()
    if direction not in VALID_DIRECTIONS:
        direction = default_direction

    sort_key = requested_sort if requested_sort in allowed_sorts else default_sort
    if sort_key:
        queryset = queryset.order_by(*build_ordering(allowed_sorts[sort_key], direction))

    return queryset, {
        "sort": sort_key or "",
        "direction": direction,
        "links": build_sort_links(request, allowed_sorts, sort_key, direction),
    }


def build_ordering(fields, direction):
    ordering = []
    for field in fields:
        field_name = field.lstrip("-")
        ordering.append(f"-{field_name}" if direction == "desc" else field_name)
    return ordering


def build_sort_links(request, allowed_sorts, current_sort, current_direction):
    links = {}
    for sort_key in allowed_sorts:
        query_params = request.GET.copy()
        query_params.pop("page", None)
        next_direction = (
            "desc"
            if current_sort == sort_key and current_direction == "asc"
            else "asc"
        )
        query_params["sort"] = sort_key
        query_params["direction"] = next_direction
        links[sort_key] = query_params.urlencode()
    return links
