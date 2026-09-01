from pathlib import Path

from django import forms

from .models import Document


ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
ALLOWED_DOCUMENT_CONTENT_TYPES = {
    "application/msword",
    "application/octet-stream",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
}
COMPLIANCE_MAX_FILE_SIZE = 10 * 1024 * 1024
SERVICE_LOG_ATTACHMENT_MAX_FILE_SIZE = 5 * 1024 * 1024
SERVICE_LOG_ATTACHMENT_MAX_FILES = 3


def validate_uploaded_document(
    uploaded_file,
    max_file_size=COMPLIANCE_MAX_FILE_SIZE,
    enforce_content_type=True,
):
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise forms.ValidationError("Unsupported file type.")
    if uploaded_file.size > max_file_size:
        max_size_mb = max_file_size // (1024 * 1024)
        raise forms.ValidationError(f"File size cannot exceed {max_size_mb} MB.")

    content_type = getattr(uploaded_file, "content_type", "")
    if enforce_content_type and content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise forms.ValidationError("Unsupported file type.")

    return uploaded_file


def validate_service_log_attachments(files):
    if len(files) > SERVICE_LOG_ATTACHMENT_MAX_FILES:
        raise forms.ValidationError("Attach no more than 3 files.")
    for uploaded_file in files:
        validate_uploaded_document(
            uploaded_file,
            max_file_size=SERVICE_LOG_ATTACHMENT_MAX_FILE_SIZE,
        )
    return files


class DocumentForm(forms.ModelForm):
    ALLOWED_EXTENSIONS = ALLOWED_DOCUMENT_EXTENSIONS
    MAX_FILE_SIZE = COMPLIANCE_MAX_FILE_SIZE

    class Meta:
        model = Document
        fields = [
            "title",
            "category",
            "file",
            "participant",
            "worker",
            "invoice",
            "service_log",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        return validate_uploaded_document(
            uploaded_file,
            self.MAX_FILE_SIZE,
            enforce_content_type=False,
        )

    def clean(self):
        cleaned_data = super().clean()
        linked_fields = ["participant", "worker", "invoice", "service_log"]
        if not any(cleaned_data.get(field) for field in linked_fields):
            raise forms.ValidationError("Select at least one linked record.")
        return cleaned_data


class WorkerDocumentUploadForm(forms.Form):
    title = forms.CharField(
        label="Document name",
        required=False,
        max_length=255,
    )
    required_document_type = forms.ChoiceField(
        label="Document type",
        required=False,
        choices=Document.RequiredDocumentType.choices,
    )
    issue_date = forms.DateField(
        label="Issue date",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    expiry_date = forms.DateField(
        label="Expiry date",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    notes = forms.CharField(
        label="Notes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    file = forms.FileField(label="File")

    def __init__(self, *args, locked_required_document_type="", **kwargs):
        self.locked_required_document_type = locked_required_document_type
        super().__init__(*args, **kwargs)
        if self.locked_required_document_type:
            self.fields["required_document_type"].initial = self.locked_required_document_type
            self.fields["required_document_type"].widget = forms.HiddenInput()
        else:
            self.fields.pop("required_document_type")
            self.fields["title"].required = True

    @property
    def is_required_document(self):
        return bool(self.locked_required_document_type)

    @property
    def selected_required_document_label(self):
        if not self.locked_required_document_type:
            return ""
        return Document.RequiredDocumentType(self.locked_required_document_type).label

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        return validate_uploaded_document(uploaded_file)

    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get("issue_date")
        expiry_date = cleaned_data.get("expiry_date")
        if issue_date and expiry_date and expiry_date < issue_date:
            self.add_error("expiry_date", "Expiry date must be after issue date.")
        if self.locked_required_document_type:
            cleaned_data["required_document_type"] = self.locked_required_document_type
        elif not cleaned_data.get("title"):
            self.add_error("title", "Enter a document name.")
        return cleaned_data
