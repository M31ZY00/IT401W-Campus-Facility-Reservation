import re
from django.core.exceptions import ValidationError

class ComplexityValidator:
    def validate(self, password, user=None):
        errors = []
        if not re.search(r"[A-Z]", password):
            errors.append("Must contain an uppercase letter.")
        if not re.search(r"\d", password):
            errors.append("Must contain a number.")
        if not re.search(r"[^A-Za-z0-9]", password):
            errors.append("Must contain a special character.")
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return "Use upper and lowercase letters, a number, and a special character."