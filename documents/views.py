from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required, worker_required

from .forms import DocumentForm
from .models import Document


@admin_required
def document_list(request):
    documents = Document.objects.select_related(
        "participant",
        "worker",
        "invoice",
        "service_log",
        "uploaded_by",
    )
    return render(
        request,
        "documents/document_list.html",
        {"documents": documents},
    )


@admin_required
def document_create(request):
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user
            document.save()
            return redirect(document)
    else:
        form = DocumentForm()

    return render(
        request,
        "documents/document_form.html",
        {"form": form},
    )


@admin_required
def document_detail(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    return render(request, "documents/document_detail.html", {"document": document})


@admin_required
def document_download(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    with document.file.open("rb") as file_handle:
        response = HttpResponse(file_handle.read(), content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{document.filename}"'
    return response


def worker_documents_for_user(user):
    worker = getattr(user, "supportworker", None)
    if not worker:
        return Document.objects.none()
    return Document.objects.filter(worker=worker)


@worker_required
def worker_document_list(request):
    documents = worker_documents_for_user(request.user)
    return render(
        request,
        "documents/worker_document_list.html",
        {"documents": documents},
    )


@worker_required
def worker_document_detail(request, document_id):
    document = get_object_or_404(worker_documents_for_user(request.user), id=document_id)
    return render(request, "documents/worker_document_detail.html", {"document": document})


@worker_required
def worker_document_download(request, document_id):
    document = get_object_or_404(worker_documents_for_user(request.user), id=document_id)
    with document.file.open("rb") as file_handle:
        response = HttpResponse(file_handle.read(), content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{document.filename}"'
    return response
