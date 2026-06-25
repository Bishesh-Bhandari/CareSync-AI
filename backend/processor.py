# ── Symptom keyword mapping ──
SYMPTOM_KEYWORDS = {
    'Headache': ['headache', 'head pain', 'head ache', 'migraine', 'head throbbing', 'head pounding'],
    'Fatigue': ['fatigue', 'tired', 'tiredness', 'exhausted', 'exhaustion', 'no energy', 'low energy', 'drained', 'lethargic'],
    'Nausea': ['nausea', 'feeling sick', 'queasy', 'sick to stomach', 'want to vomit', 'nauseous'],
    'Dizziness': ['dizziness', 'dizzy', 'lightheaded', 'light headed', 'room spinning', 'vertigo'],
    'Chest Pain': ['chest pain', 'chest tightness', 'chest pressure', 'chest ache'],
    'Shortness of Breath': ['shortness of breath', 'breathless', 'hard to breathe', 'can\'t breathe', 'wheezing'],
    'Fever': ['fever', 'temperature', 'high temp', 'chills', 'hot and cold', 'sweating'],
    'Cough': ['cough', 'coughing', 'dry cough', 'wet cough', 'persistent cough'],
    'Joint Pain': ['joint pain', 'joint ache', 'stiff joints', 'arthritis', 'knee pain', 'elbow pain'],
    'Back Pain': ['back pain', 'backache', 'lower back pain', 'upper back pain', 'spine pain'],
    'Insomnia': ['insomnia', 'can\'t sleep', 'cannot sleep', 'sleep difficulty', 'trouble sleeping', 'awake all night', 'no sleep'],
    'Anxiety': ['anxiety', 'anxious', 'worried', 'panic', 'nervous', 'restless', 'on edge'],
    'Stomach Pain': ['stomach pain', 'abdominal pain', 'stomach ache', 'belly pain', 'cramps'],
    'Appetite Loss': ['loss of appetite', 'no appetite', 'not eating', 'don\'t want to eat', 'skipping meals'],
    'Blurred Vision': ['blurred vision', 'blurry vision', 'vision problems', 'can\'t see clearly', 'floaters'],
}

# ── Severity modifier keywords ──
SEVERITY_WORDS = {
    'severe': 3, 'extreme': 3, 'intense': 3, 'unbearable': 4, 'terrible': 3,
    'horrible': 3, 'worst': 4, 'excruciating': 4, 'agonizing': 4, 'very bad': 3,
    'bad': 2, 'strong': 2, 'significant': 2, 'noticeable': 1, 'troubling': 1,
    'moderate': 1, 'medium': 1, 'some': 0, 'mild': -1, 'slight': -1,
    'minor': -1, 'little': -1, 'low': -1, 'light': -1, 'barely': -2,
    'tiny': -2, 'very mild': -2, 'barely any': -2,
}

MOOD_WORDS = {
    'good': ['good', 'great', 'fine', 'well', 'better', 'happy', 'excellent', 'amazing', 'fantastic'],
    'okay': ['okay', 'ok', 'alright', 'so-so', 'fair', 'decent', 'neutral'],
    'bad': ['bad', 'terrible', 'awful', 'depressed', 'sad', 'low', 'miserable', 'horrible', 'worst'],
}

MEDICATION_KEYWORDS = ['mg', 'tablet', 'capsule', 'pill', 'dose', 'ibuprofen', 'paracetamol', 'aspirin',
                        'amoxicillin', 'metformin', 'lisinopril', 'atorvastatin', 'omeprazole',
                        'prednisone', 'antibiotic', 'painkiller', 'medicine', 'medication', 'prescription']


def parse_symptoms(text):
    """Parse symptom text and return list of {name, severity} dicts."""
    text_lower = text.lower()
    found = []

    for symptom_name, keywords in SYMPTOM_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                base_severity = 5
                for word, mod in SEVERITY_WORDS.items():
                    if word in text_lower:
                        base_severity += mod
                base_severity = max(1, min(10, base_severity))
                found.append({'name': symptom_name, 'severity': base_severity})
                break

    if not found:
        found.append({'name': 'Unspecified', 'severity': 5})

    return found


def calculate_overall_severity(symptoms):
    """Calculate overall severity from parsed symptoms (1-10)."""
    if not symptoms:
        return 5
    total = sum(s['severity'] for s in symptoms)
    avg = total / len(symptoms)
    count_bonus = min(2, len(symptoms) - 1) * 0.5
    return max(1, min(10, round(avg + count_bonus)))


def detect_mood(text):
    """Detect mood from text."""
    text_lower = text.lower()
    for mood, words in MOOD_WORDS.items():
        for word in words:
            if word in text_lower:
                return mood
    return 'okay'


def detect_trend(checkins):
    """Detect health trend from checkin history. Returns (trend, percent)."""
    if len(checkins) < 2:
        return 'stable', 0

    ordered = sorted(checkins, key=lambda c: c['created_at'])
    first_half = ordered[:len(ordered) // 2]
    second_half = ordered[len(ordered) // 2:]

    avg_first = sum(c['severity'] for c in first_half) / len(first_half)
    avg_second = sum(c['severity'] for c in second_half) / len(second_half)

    if avg_first == 0:
        return 'stable', 0

    change = ((avg_first - avg_second) / avg_first) * 100

    if change > 10:
        return 'improving', round(change)
    elif change < -10:
        return 'worsening', round(abs(change))
    else:
        return 'stable', round(abs(change))


def build_symptom_matrix(checkins):
    """Build a 2D matrix for the heatmap. Returns {symptoms, dates, matrix}."""
    ordered = sorted(checkins, key=lambda c: c['created_at'])
    if not ordered:
        return {'symptoms': [], 'dates': [], 'matrix': []}

    import json
    all_symptoms = set()
    parsed_list = []
    dates = []

    for c in ordered:
        parsed = json.loads(c.get('symptoms_parsed', '[]'))
        parsed_list.append(parsed)
        dates.append(c['created_at'][:10])
        for s in parsed:
            if s['name'] != 'Unspecified':
                all_symptoms.add(s['name'])

    symptoms = sorted(all_symptoms)
    matrix = []

    for symptom in symptoms:
        row = []
        for parsed in parsed_list:
            val = 0
            for s in parsed:
                if s['name'] == symptom:
                    val = s['severity']
                    break
            row.append(val)
        matrix.append(row)

    return {'symptoms': symptoms, 'dates': dates, 'matrix': matrix}