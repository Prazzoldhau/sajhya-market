import json
from collections import Counter

from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import content
from .decorators import summit_staff_required, table_required
from .models import SessionSubmission, Table


# ---------------------------------------------------------------------------
# Generic step-section engine
#
# Every session is built from a small set of reusable section "types"
# (see summit_app/content.py). These two functions are the only place that
# knows how each type maps to (a) form-field names / pre-filled values for
# rendering, and (b) how posted data is parsed back into the submission's
# JSON blob. Templates never invent field names -- they always render
# whatever `field_name` build_section_context() computed.
# ---------------------------------------------------------------------------

def build_section_context(section, submission, step_key, session_key):
    name = section["name"]
    section_type = section["type"]
    step_data = submission.data.get(step_key, {}) or {}
    base_name = f"{step_key}:{name}"
    ctx = {"type": section_type, "label": section.get("label", ""), "name": name}

    if section_type == "checklist_other":
        selected = step_data.get(name, [])
        options = [{"key": k, "label": lbl, "checked": k in selected} for k, lbl in section["options"]]
        ctx.update(
            field_name=base_name,
            options=options,
            other_checked="other" in selected,
            other_text=step_data.get(f"{name}_other_text", ""),
            other_field_name=f"{base_name}:other_text",
        )
    elif section_type in ("score_for_prior", "top_n_select"):
        source_step, source_field = section["source_step"], section["source_field"]
        prior_data = submission.data.get(source_step, {}) or {}
        chosen = prior_data.get(source_field, [])
        prior_other_text = prior_data.get(f"{source_field}_other_text", "")
        label_map = dict(content.get_section_options(session_key, source_step, source_field))
        if section_type == "score_for_prior":
            scores = step_data.get(name, {})
            items = [
                {
                    "key": key,
                    "label": prior_other_text if key == "other" and prior_other_text else label_map.get(key, key),
                    "field_name": f"{base_name}:{key}",
                    "value": scores.get(key, ""),
                }
                for key in chosen
            ]
        else:
            selected = step_data.get(name, [])
            items = [
                {
                    "key": key,
                    "label": prior_other_text if key == "other" and prior_other_text else label_map.get(key, key),
                    "field_name": f"{base_name}:{key}",
                    "checked": key in selected,
                }
                for key in chosen
            ]
        ctx.update(items=items, empty=not chosen, n=section.get("n", 3))
    elif section_type == "free_text":
        ctx.update(field_name=base_name, value=step_data.get(name, ""), rows=section.get("rows", 3))
    elif section_type == "text_fields":
        values = step_data.get(name, {})
        ctx["fields"] = [
            {"key": key, "label": lbl, "field_name": f"{base_name}:{key}", "value": values.get(key, "")}
            for key, lbl in section["fields"]
        ]
    elif section_type == "number_fields":
        values = step_data.get(name, {})
        ctx["fields"] = [
            {"key": key, "label": lbl, "suffix": suf, "field_name": f"{base_name}:{key}", "value": values.get(key, "")}
            for key, lbl, suf in section["fields"]
        ]
    elif section_type == "radio":
        selected = step_data.get(name, "")
        options = [{"key": k, "label": lbl, "checked": k == selected} for k, lbl in section["options"]]
        ctx.update(
            field_name=base_name,
            options=options,
            has_other=any(k == "other" for k, _ in section["options"]),
            other_checked=selected == "other",
            other_text=step_data.get(f"{name}_other_text", ""),
            other_field_name=f"{base_name}:other_text",
        )
    elif section_type == "text":
        value = submission.facilitator_name if name == "facilitator_name" else step_data.get(name, "")
        ctx.update(field_name=base_name, value=value)
    return ctx


def parse_section(request, section, step_key, submission):
    name = section["name"]
    section_type = section["type"]
    base_name = f"{step_key}:{name}"
    step_data = submission.data.setdefault(step_key, {})

    if section_type == "checklist_other":
        selected = request.POST.getlist(base_name)
        other_text = request.POST.get(f"{base_name}:other_text", "").strip()
        if other_text and "other" not in selected:
            selected.append("other")
        step_data[name] = selected
        step_data[f"{name}_other_text"] = other_text
    elif section_type == "score_for_prior":
        source_step, source_field = section["source_step"], section["source_field"]
        chosen = submission.data.get(source_step, {}).get(source_field, [])
        scores = {}
        for key in chosen:
            raw = request.POST.get(f"{base_name}:{key}", "").strip()
            if raw:
                try:
                    val = int(raw)
                except ValueError:
                    continue
                if 1 <= val <= 5:
                    scores[key] = val
        step_data[name] = scores
    elif section_type == "top_n_select":
        source_step, source_field = section["source_step"], section["source_field"]
        chosen = submission.data.get(source_step, {}).get(source_field, [])
        step_data[name] = [key for key in chosen if request.POST.get(f"{base_name}:{key}") == "on"]
    elif section_type == "free_text":
        step_data[name] = request.POST.get(base_name, "").strip()
    elif section_type == "text_fields":
        step_data[name] = {key: request.POST.get(f"{base_name}:{key}", "").strip() for key, _ in section["fields"]}
    elif section_type == "number_fields":
        step_data[name] = {key: request.POST.get(f"{base_name}:{key}", "").strip() for key, _, _ in section["fields"]}
    elif section_type == "radio":
        step_data[name] = request.POST.get(base_name, "")
        step_data[f"{name}_other_text"] = request.POST.get(f"{base_name}:other_text", "").strip()
    elif section_type == "text":
        value = request.POST.get(base_name, "").strip()
        if name == "facilitator_name":
            submission.facilitator_name = value
        else:
            step_data[name] = value


def find_missing_prerequisite(session_key, step, submission):
    """If this step reads an earlier step's checklist (score_for_prior /
    top_n_select) that hasn't been filled in yet, return that earlier
    step's number so the view can bounce the facilitator back to it."""
    session = content.get_session(session_key)
    for section in step["sections"]:
        source_step = section.get("source_step")
        if not source_step:
            continue
        source_field = section["source_field"]
        if not submission.data.get(source_step, {}).get(source_field):
            src_step_obj = content.get_step_by_key(session_key, source_step)
            return session["steps"].index(src_step_obj) + 1
    return None


# ---------------------------------------------------------------------------
# Table-facing views
# ---------------------------------------------------------------------------

def _session_table(request):
    """The table this device/browser is already checked into this session, if any.
    Clears a stale id (e.g. table was deleted) instead of leaving it dangling."""
    table_id = request.session.get("summit_table_id")
    if not table_id:
        return None
    table = Table.objects.filter(id=table_id).first()
    if table is None:
        request.session.pop("summit_table_id", None)
    return table


def choose_table(request):
    bound_table = _session_table(request)
    if bound_table:
        return redirect("summit-table-dashboard", table_number=bound_table.number)

    if request.method == "POST":
        table_number = request.POST.get("table_number")
        table = Table.objects.filter(number=table_number).first()
        if table is None:
            messages.error(request, "That table doesn't exist.")
        elif table.is_claimed:
            messages.error(request, f"Table {table.number} is already taken. Pick another table.")
        else:
            table.claim()
            return redirect("summit-table-login", table_number=table.number)
        return redirect("summit-choose-table")

    tables = list(Table.objects.all())
    return render(request, "summit/choose_table.html", {"tables": tables, "event_title": content.EVENT_TITLE})


def table_login(request, table_number):
    table = get_object_or_404(Table, number=table_number)

    bound_table = _session_table(request)
    if bound_table:
        if bound_table.id != table.id:
            messages.info(
                request,
                f"This device is already checked in to Table {bound_table.number}. Log out there first to switch tables.",
            )
        return redirect("summit-table-dashboard", table_number=bound_table.number)

    if request.method == "POST":
        pin = request.POST.get("pin", "").strip()
        if table.check_pin(pin):
            request.session["summit_table_id"] = table.id
            return redirect("summit-table-dashboard", table_number=table_number)
        messages.error(request, "Incorrect PIN. Please try again.")
    return render(request, "summit/table_login.html", {"table": table, "event_title": content.EVENT_TITLE})


@table_required
def table_logout(request, table_number):
    request.session.pop("summit_table_id", None)
    return redirect("summit-table-login", table_number=table_number)


@table_required
def leave_table(request, table_number):
    """Self-service opposite of Logout: also frees the table's claim so
    another group can pick it from the chooser, e.g. if this group chose
    the wrong table by mistake. Worksheet answers already entered are kept
    (same as the staff-only release_table action) -- only the claim is reset."""
    table = request.summit_table
    if request.method == "POST":
        table.release()
        request.session.pop("summit_table_id", None)
        messages.success(request, f"You've left Table {table.number}. It's now available for another group.")
        return redirect("summit-choose-table")
    return redirect("summit-table-dashboard", table_number=table_number)


@table_required
def table_dashboard(request, table_number):
    table = request.summit_table
    sessions = []
    for key in content.SESSION_ORDER:
        session = content.SESSIONS[key]
        total_steps = len(session["steps"])
        submission = SessionSubmission.objects.filter(table=table, session_key=key).first()
        if submission is None:
            status, current_step = "not_started", 1
        elif submission.is_complete:
            status, current_step = "submitted", total_steps
        else:
            status, current_step = "in_progress", submission.current_step
        sessions.append(
            {
                "key": key,
                "title": session["short_title"],
                "status": status,
                "current_step": current_step,
                "total_steps": total_steps,
            }
        )
    return render(
        request,
        "summit/table_dashboard.html",
        {"table": table, "sessions": sessions, "event_title": content.EVENT_TITLE},
    )


@table_required
def session_step(request, table_number, session_key, step_no):
    table = request.summit_table
    session = content.get_session(session_key)
    if session is None:
        raise Http404("Unknown session")
    step = content.get_step(session_key, step_no)
    if step is None:
        raise Http404("Unknown step")
    total_steps = len(session["steps"])

    submission, _ = SessionSubmission.objects.get_or_create(table=table, session_key=session_key)

    missing_step_no = find_missing_prerequisite(session_key, step, submission)
    if missing_step_no:
        messages.warning(request, "Please complete the previous step first.")
        return redirect(
            "summit-session-step", table_number=table_number, session_key=session_key, step_no=missing_step_no
        )

    if request.method == "POST":
        for section in step["sections"]:
            parse_section(request, section, step["key"], submission)

        is_last = step_no == total_steps
        if is_last:
            submission.is_complete = True
            submission.submitted_at = timezone.now()
            submission.current_step = total_steps
        else:
            submission.current_step = max(submission.current_step, step_no + 1)
        submission.save()

        if is_last:
            messages.success(request, f"{session['short_title']} submitted for {table}.")
            return redirect("summit-table-dashboard", table_number=table_number)
        return redirect(
            "summit-session-step", table_number=table_number, session_key=session_key, step_no=step_no + 1
        )

    sections_ctx = [build_section_context(s, submission, step["key"], session_key) for s in step["sections"]]
    context = {
        "table": table,
        "session_key": session_key,
        "session": session,
        "step": step,
        "step_no": step_no,
        "total_steps": total_steps,
        "sections": sections_ctx,
        "event_title": content.EVENT_TITLE,
        "progress_pct": int(step_no / total_steps * 100),
        "is_last_step": step_no == total_steps,
    }
    return render(request, "summit/session_step.html", context)


# ---------------------------------------------------------------------------
# Admin-facing views (staff only) -- plain numbers/tables, no charts.
# ---------------------------------------------------------------------------

@summit_staff_required
def release_table(request, table_number):
    table = get_object_or_404(Table, number=table_number)
    if request.method == "POST":
        table.release()
        messages.success(request, f"Table {table.number} is now available again.")
    return redirect("summit-admin-dashboard")


@summit_staff_required
def reset_table_sessions(request, table_number):
    table = get_object_or_404(Table, number=table_number)
    if request.method == "POST":
        deleted, _ = SessionSubmission.objects.filter(table=table).delete()
        messages.success(request, f"Cleared {deleted} worksheet submission(s) for Table {table.number}.")
    return redirect("summit-admin-dashboard")


@summit_staff_required
def admin_dashboard(request):
    tables = list(Table.objects.all())
    rows = []
    for key in content.SESSION_ORDER:
        session = content.SESSIONS[key]
        submitted_count = 0
        cells = []
        for table in tables:
            submission = SessionSubmission.objects.filter(table=table, session_key=key).first()
            if submission is None:
                status = "not_started"
            elif submission.is_complete:
                status = "submitted"
                submitted_count += 1
            else:
                status = "in_progress"
            cells.append({"table": table, "status": status})
        rows.append(
            {
                "key": key,
                "title": session["short_title"],
                "cells": cells,
                "submitted_count": submitted_count,
                "total_tables": len(tables),
            }
        )
    return render(
        request,
        "summit/admin_dashboard.html",
        {"rows": rows, "tables": tables, "event_title": content.EVENT_TITLE},
    )


@summit_staff_required
def admin_session_summary(request, session_key):
    session = content.get_session(session_key)
    if session is None:
        raise Http404("Unknown session")

    submissions = list(SessionSubmission.objects.filter(session_key=session_key).select_related("table"))
    total_tables = Table.objects.count()
    submitted_count = sum(1 for s in submissions if s.is_complete)

    causes_options = dict(content.get_section_options(session_key, "step1", "causes"))
    score_sum, score_count, score_labels = Counter(), Counter(), {}
    top3_tally = Counter()
    for s in submissions:
        step1 = s.data.get("step1", {})
        step2 = s.data.get("step2", {})
        other_text = step1.get("causes_other_text", "")
        for key, val in step2.get("impact_scores", {}).items():
            label = other_text if key == "other" and other_text else causes_options.get(key, key)
            score_labels[key] = label
            score_sum[key] += val
            score_count[key] += 1
        for key in step2.get("top3", []):
            label = other_text if key == "other" and other_text else causes_options.get(key, key)
            top3_tally[label] += 1

    impact_rows = [
        {"label": score_labels[key], "average": round(total / score_count[key], 1), "count": score_count[key]}
        for key, total in score_sum.items()
    ]
    impact_rows.sort(key=lambda r: -r["average"])

    checklist_frequency = []
    for step in session["steps"]:
        for section in step["sections"]:
            if section["type"] == "checklist_other" and section["name"] != "causes":
                counter = Counter()
                option_labels = dict(section["options"])
                for s in submissions:
                    for key in s.data.get(step["key"], {}).get(section["name"], []):
                        counter[option_labels.get(key, "Other")] += 1
                if counter:
                    checklist_frequency.append({"label": section["label"], "counts": counter.most_common()})
            elif section["type"] == "radio":
                counter = Counter()
                option_labels = dict(section["options"])
                for s in submissions:
                    val = s.data.get(step["key"], {}).get(section["name"], "")
                    if val:
                        counter[option_labels.get(val, val)] += 1
                if counter:
                    checklist_frequency.append({"label": section["label"], "counts": counter.most_common()})

    raw_rows = [
        {
            "table": s.table,
            "is_complete": s.is_complete,
            "current_step": s.current_step,
            "total_steps": len(session["steps"]),
            "facilitator_name": s.facilitator_name,
            "submitted_at": s.submitted_at,
            "data_json": json.dumps(s.data, indent=2, ensure_ascii=False),
        }
        for s in submissions
    ]

    context = {
        "session": session,
        "session_key": session_key,
        "submitted_count": submitted_count,
        "total_tables": total_tables,
        "impact_rows": impact_rows,
        "top3_tally": top3_tally.most_common(),
        "checklist_frequency": checklist_frequency,
        "raw_rows": raw_rows,
        "event_title": content.EVENT_TITLE,
    }
    return render(request, "summit/admin_session_summary.html", context)


# ---------------------------------------------------------------------------
# Admin-facing live results (staff only) -- polling-based charts + table-wise
# breakdowns, refreshed while facilitators are still filling in their tables.
# ---------------------------------------------------------------------------

def _live_question(session_key, step, section, tables, submissions):
    """Build one question's worth of live-results data: an overall tally
    (for the chart) plus a per-table breakdown row, for any section type."""
    name = section["name"]
    section_type = section["type"]
    step_key = step["key"]
    base = {
        "step_key": step_key,
        "name": name,
        "label": section.get("label") or name,
        "type": section_type,
    }

    if section_type in ("checklist_other", "radio"):
        options = section["options"]
        tally = Counter({lbl: 0 for _, lbl in options})
        option_labels = dict(options)
        table_rows = []
        for table in tables:
            sub = submissions.get(table.id)
            step_data = (sub.data.get(step_key, {}) or {}) if sub else {}
            if section_type == "checklist_other":
                selected = step_data.get(name, [])
            else:
                val = step_data.get(name, "")
                selected = [val] if val else []
            if not selected:
                continue
            other_text = step_data.get(f"{name}_other_text", "")
            labels = [other_text if k == "other" and other_text else option_labels.get(k, k) for k in selected]
            for lbl in labels:
                tally[lbl] += 1
            table_rows.append({"table": str(table), "value": ", ".join(labels)})
        base.update(
            chartable=True,
            chart_labels=list(tally.keys()),
            chart_values=list(tally.values()),
            table_rows=table_rows,
        )
        return base

    if section_type in ("score_for_prior", "top_n_select"):
        source_step, source_field = section["source_step"], section["source_field"]
        label_map = dict(content.get_section_options(session_key, source_step, source_field))
        table_rows = []
        if section_type == "score_for_prior":
            score_sum, score_count = Counter(), Counter()
            for table in tables:
                sub = submissions.get(table.id)
                if sub is None:
                    continue
                scores = (sub.data.get(step_key, {}) or {}).get(name, {})
                if not scores:
                    continue
                source_data = sub.data.get(source_step, {}) or {}
                other_text = source_data.get(f"{source_field}_other_text", "")
                parts = []
                for key, val in scores.items():
                    lbl = other_text if key == "other" and other_text else label_map.get(key, key)
                    score_sum[lbl] += val
                    score_count[lbl] += 1
                    parts.append(f"{lbl}: {val}")
                table_rows.append({"table": str(table), "value": ", ".join(parts)})
            chart_labels = list(score_sum.keys())
            chart_values = [round(score_sum[k] / score_count[k], 1) for k in chart_labels]
        else:
            tally = Counter()
            for table in tables:
                sub = submissions.get(table.id)
                if sub is None:
                    continue
                chosen = (sub.data.get(step_key, {}) or {}).get(name, [])
                if not chosen:
                    continue
                source_data = sub.data.get(source_step, {}) or {}
                other_text = source_data.get(f"{source_field}_other_text", "")
                labels = [other_text if k == "other" and other_text else label_map.get(k, k) for k in chosen]
                for lbl in labels:
                    tally[lbl] += 1
                table_rows.append({"table": str(table), "value": ", ".join(labels)})
            chart_labels = list(tally.keys())
            chart_values = list(tally.values())
        base.update(chartable=True, chart_labels=chart_labels, chart_values=chart_values, table_rows=table_rows)
        return base

    # free_text, text_fields, number_fields, text -- not chartable as votes,
    # shown as a live-updating per-table response list instead.
    table_rows = []
    for table in tables:
        sub = submissions.get(table.id)
        if sub is None:
            continue
        if section_type == "text" and name == "facilitator_name":
            value = sub.facilitator_name
        else:
            step_data = sub.data.get(step_key, {}) or {}
            raw = step_data.get(name)
            if section_type in ("free_text", "text"):
                value = raw or ""
            elif section_type == "text_fields":
                value = "; ".join(f"{lbl}: {raw.get(key, '')}" for key, lbl in section["fields"] if raw and raw.get(key))
            else:  # number_fields
                value = "; ".join(f"{lbl}: {raw.get(key, '')}" for key, lbl, _ in section["fields"] if raw and raw.get(key))
        if value:
            table_rows.append({"table": str(table), "value": value})
    base.update(chartable=False, chart_labels=[], chart_values=[], table_rows=table_rows)
    return base


@summit_staff_required
def admin_live_results(request):
    return render(
        request,
        "summit/admin_live_results.html",
        {
            "session_order": content.SESSION_ORDER,
            "sessions": content.SESSIONS,
            "tables": list(Table.objects.all()),
            "event_title": content.EVENT_TITLE,
        },
    )


@summit_staff_required
def admin_live_results_data(request):
    tables = list(Table.objects.all())
    total_tables = len(tables)

    sessions_payload = []
    for session_key in content.SESSION_ORDER:
        session = content.SESSIONS[session_key]
        submissions = {
            s.table_id: s
            for s in SessionSubmission.objects.filter(session_key=session_key).select_related("table")
        }
        submitted_count = sum(1 for s in submissions.values() if s.is_complete)
        questions = [
            _live_question(session_key, step, section, tables, submissions)
            for step in session["steps"]
            for section in step["sections"]
        ]
        sessions_payload.append(
            {
                "session_key": session_key,
                "title": session["short_title"],
                "submitted_count": submitted_count,
                "total_tables": total_tables,
                "questions": questions,
            }
        )

    return JsonResponse(
        {
            "total_tables": total_tables,
            "generated_at": timezone.now().strftime("%H:%M:%S"),
            "sessions": sessions_payload,
        }
    )
