from django.core.paginator import Paginator


DEFAULT_PAGE_SIZE = 20


def paginate_queryset(request, queryset, per_page=DEFAULT_PAGE_SIZE):
    page_obj = Paginator(queryset, per_page).get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return page_obj, {
        "page_obj": page_obj,
        "page_query": query_params.urlencode(),
        "record_start": page_obj.start_index(),
        "record_end": page_obj.end_index(),
        "record_count": page_obj.paginator.count,
    }
