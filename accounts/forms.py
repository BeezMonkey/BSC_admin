from django.contrib.auth.forms import SetPasswordForm


class AdminSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "New password"
        self.fields["new_password2"].label = "Confirm password"
