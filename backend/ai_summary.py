from db import get_checkins, save_summary
from processor import detect_trend, build_symptom_matrix
import json


def generate_clinical_summary(user_id):
    """Generate a rule-based clinical summary from checkin history."""
    checkins = get_checkins(user_id, limit=20)
    if not checkins:
        return None

    ordered = sorted(checkins, key=lambda c: c['created_at'])
    total = len(ordered)
    first = ordered[0]
    last = ordered[-1]

    trend, trend_pct = detect_trend(checkins)
    matrix_data = build_symptom_matrix(checkins)

    # ── Build summary text ──
    lines = []

    # Opening
    lines.append(f"Clinical summary based on {total} check-in entries.")
    lines.append(f"Monitoring period: {first['created_at'][:10]} to {last['created_at'][:10]}.")
    lines.append("")

    # Trend statement
    trend_map = {
        'improving': f"Overall trend: IMPROVING ({trend_pct}% reduction in severity).",
        'worsening': f"Overall trend: WORSENING ({trend_pct}% increase in severity).",
        'stable': f"Overall trend: STABLE (less than 10% change in severity)."
    }
    lines.append(trend_map.get(trend, trend_map['stable']))
    lines.append("")

    # Per-symptom analysis
    if matrix_data['symptoms']:
        lines.append("Symptom breakdown:")
        for i, symptom in enumerate(matrix_data['symptoms']):
            row = matrix_data['matrix'][i]
            first_val = row[0] if row[0] > 0 else None
            last_val = row[-1] if row[-1] > 0 else None
            appearances = sum(1 for v in row if v > 0)

            if first_val and last_val:
                diff = first_val - last_val
                if diff > 2:
                    status = "significantly improved"
                elif diff > 0:
                    status = "slightly improved"
                elif diff == 0:
                    status = "unchanged"
                elif diff > -2:
                    status = "slightly worsened"
                else:
                    status = "significantly worsened"
                lines.append(f"  - {symptom}: {status} (first: {first_val}/10, latest: {last_val}/10, present in {appearances}/{total} entries)")
            elif first_val and not last_val:
                lines.append(f"  - {symptom}: RESOLVED (was {first_val}/10, absent in latest entries, present in {appearances}/{total} entries)")
            elif not first_val and last_val:
                lines.append(f"  - {symptom}: NEW symptom (now {last_val}/10, present in {appearances}/{total} entries)")
            else:
                lines.append(f"  - {symptom}: intermittent (present in {appearances}/{total} entries)")
        lines.append("")

    # New symptoms flag
    if matrix_data['symptoms']:
        for i, symptom in enumerate(matrix_data['symptoms']):
            row = matrix_data['matrix'][i]
            first_half = row[:len(row) // 2] if len(row) > 1 else row
            second_half = row[len(row) // 2:] if len(row) > 1 else []
            if not any(v > 0 for v in first_half) and any(v > 0 for v in second_half):
                lines.append(f"FLAG: New symptom '{symptom}' appeared in recent check-ins. Requires attention.")
                lines.append("")

    # Medication note
    meds_mentioned = set()
    for c in ordered:
        if c.get('medications') and c['medications'].strip():
            meds_mentioned.add(c['medications'].strip())
    if meds_mentioned:
        lines.append(f"Medications reported: {', '.join(meds_mentioned)}")
        # Check for side effect keywords in recent entries
        recent_text = " ".join(c['symptoms_text'].lower() for c in ordered[-3:])
        side_effect_words = ['nausea', 'dizziness', 'headache', 'stomach pain', 'rash']
        found_side_effects = [w for w in side_effect_words if w in recent_text]
        if found_side_effects:
            lines.append(f"Note: Possible medication side effects detected: {', '.join(found_side_effects)}")
        lines.append("")

    # Current status
    last_parsed = json.loads(last.get('symptoms_parsed', '[]'))
    active = [s['name'] for s in last_parsed if s['name'] != 'Unspecified']
    lines.append(f"Current status: Severity {last['severity']}/10, Health Score {last['health_score']}/100.")
    lines.append(f"Active symptoms: {', '.join(active) if active else 'None reported.'}")
    lines.append(f"Latest mood: {last.get('mood', 'not reported')}.")

    summary_text = "\n".join(lines)

    # Save to DB
    save_summary(user_id, summary_text, trend, trend_pct)

    return {
        'text': summary_text,
        'trend': trend,
        'trend_percent': trend_pct,
        'total_checkins': total,
        'period_start': first['created_at'][:10],
        'period_end': last['created_at'][:10]
    }