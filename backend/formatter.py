import json
from processor import detect_trend, build_symptom_matrix

def format_checkin(checkin):
    parsed = json.loads(checkin.get('symptoms_parsed', '[]'))
    return {
        'id': checkin['id'],
        'date': checkin['created_at'][:10],
        'datetime': checkin['created_at'],
        'text': checkin['symptoms_text'],
        'symptoms': parsed,
        'severity': checkin['severity'],
        'health_score': checkin['health_score'],
        'mood': checkin.get('mood', 'okay'),
        'medications': checkin.get('medications', ''),
        'notes': checkin.get('notes', '')
    }

def format_chart_data(checkins):
    ordered = sorted(checkins, key=lambda c: c['created_at'])
    labels = [c['created_at'][:10] for c in ordered]
    scores = [c['health_score'] for c in ordered]
    severities = [c['severity'] for c in ordered]
    return {'labels': labels, 'scores': scores, 'severities': severities}

def format_heatmap_data(checkins):
    return build_symptom_matrix(checkins)

def format_dashboard_data(user, checkins, summary):
    formatted_checkins = [format_checkin(c) for c in checkins]
    chart_data = format_chart_data(checkins)
    heatmap_data = format_heatmap_data(checkins)

    trend, trend_pct = detect_trend(checkins) if len(checkins) >= 2 else ('stable', 0)

    latest = formatted_checkins[0] if formatted_checkins else None
    active_symptoms = [s for s in latest['symptoms'] if s['name'] != 'Unspecified'] if latest else []

    return {
        'user': {
            'id': user['id'],
            'name': user['full_name'],
            'username': user['username'],
            'email': user['email'],
            'role': user.get('role', 'patient'),
            'member_since': user['created_at'][:10],
            'total_checkins': user.get('total_checkins', len(checkins))
        },
        'latest': latest,
        'trend': trend,
        'trend_percent': trend_pct,
        'active_symptoms': active_symptoms,
        'chart': chart_data,
        'heatmap': heatmap_data,
        'summary': summary,
        'checkins': formatted_checkins
    }