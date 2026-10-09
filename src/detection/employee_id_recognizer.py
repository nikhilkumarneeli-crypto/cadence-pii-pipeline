
from presidio_analyzer import Pattern, PatternRecognizer


class EmployeeIdRecognizer(PatternRecognizer):
    def __init__(self):
        patterns = [
            Pattern(
                name="employee_id_pattern",
                regex=r"\bEMP-\d{5}\b",
                score=0.8,
            )
        ]

        super().__init__(
            supported_entity="EMPLOYEE_ID",
            patterns=patterns,
            context=[
                "employee id",
                "employee number",
                "employee no",
                "staff id",
            ],
        )
