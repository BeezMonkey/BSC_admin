from pathlib import Path

from django import forms

from .models import Document


class DocumentForm(forms.ModelForm):
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    MAX_FILE_SIZE = 10 * 1024 * 1024

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
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            raise forms.ValidationError("Unsupported file type.")
        if uploaded_file.size > self.MAX_FILE_SIZE:
            raise forms.ValidationError("File size cannot exceed 10 MB.")
        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()
        linked_fields = ["participant", "worker", "invoice", "service_log"]
        if not any(cleaned_data.get(field) for field in linked_fields):
            raise forms.ValidationError("Select at least one linked record.")
        return cleaned_data
