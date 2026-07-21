import re

MEDICAL_KEYWORDS = {
    "symptom",
    "symptoms",
    "diagnosis",
    "diagnose",
    "disease",
    "disorder",
    "condition",
    "treatment",
    "medication",
    "medicine",
    "drug",
    "dose",
    "dosage",
    "therapy",
    "patient",
    "clinical",
    "doctor",
    "physician",
    "hospital",
    "health",
    "medical",
    "pain",
    "fever",
    "infection",
    "virus",
    "bacteria",
    "cancer",
    "diabetes",
    "hypertension",
    "anemia",
    "injury",
    "wound",
    "allergy",
    "vaccine",
    "pregnancy",
    "blood",
    "heart",
    "lung",
    "liver",
    "kidney",
    "mental health",
    "depression",
    "anxiety",
}

OFF_TOPIC_PATTERNS = (
    re.compile(r"\b(write|generate|create)\b.+\b(code|script|program|essay|poem|story)\b", re.I),
    re.compile(r"\b(recipe|joke|horoscope|stock|crypto|bitcoin)\b", re.I),
    re.compile(r"\b(translate|summarize).+\b(document|article|book)\b", re.I),
    re.compile(r"\bignore (all )?(previous|prior) instructions\b", re.I),
    re.compile(r"\b(you are now|act as|pretend to be)\b", re.I),
    re.compile(r"\b(hack|crack|exploit|malware|password)\b", re.I),
)

MEDICAL_QUESTION_PATTERNS = (
    re.compile(r"\bwhat (are|is) (the )?(symptoms|signs|causes|treatments|risk factors)\b", re.I),
    re.compile(r"\bhow (do|can|should) (i|you) (treat|prevent|manage)\b", re.I),
    re.compile(r"\bis .+ (normal|dangerous|contagious|curable)\b", re.I),
    re.compile(r"\b(side effects|drug interaction|contraindication)\b", re.I),
)


def validate_medical_question(question: str, *, enforce: bool) -> str | None:
    """Return an error message when the question should be rejected."""
    if not enforce:
        return None

    normalized = " ".join(question.lower().split())

    for pattern in OFF_TOPIC_PATTERNS:
        if pattern.search(normalized):
            return "This service only accepts medical and health-related questions."

    if any(keyword in normalized for keyword in MEDICAL_KEYWORDS):
        return None

    if any(pattern.search(normalized) for pattern in MEDICAL_QUESTION_PATTERNS):
        return None

    if normalized.endswith("?"):
        return (
            "Please ask a medical or health-related question "
            "(symptoms, conditions, treatments, medications, etc.)."
        )

    return (
        "This service only accepts medical and health-related questions "
        "(symptoms, conditions, treatments, medications, etc.)."
    )
