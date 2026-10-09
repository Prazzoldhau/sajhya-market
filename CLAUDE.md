# Sajhya — Project Notes for Claude

## Deploy (no auto-deploy on push)
SSH in and run manually:
```
git fetch origin && git reset --hard origin/main
python manage.py migrate   # only if a migration shipped
touch tmp/restart.txt
```
`{% static %}` on an uncollected file 500s in production — run `collectstatic` if a template adds a new static asset.

## Standing git workflow
Feature branch → commit (message explains *why*) → `git checkout main` → `git merge --no-ff <branch> -m "..."` → `git push origin main` → `git branch -d <branch>`.

Commit messages end with:
```
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```
PR descriptions end with:
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Adding a new tab to the Medical Profile (patient + physio editable)

The Medical Profile page (`patient_app/templates/patient-medical-profile.html`) is shared, byte-for-byte, between the patient's own view (`patient_app.views.patient_medical_profile_page`, session-based) and the physio-facing editor (`detail_app.views.physio_medical_profile_page`, `patient_id` in the URL). Existing tabs: Medication, Blood Tests, Physiotherapy (Assessment/Exercises/Aids sub-tabs), Medical Record, Nursing, Diet Chart. To add a new one, follow this recipe rather than re-deriving the architecture:

1. **Model** (`personal_account/models.py`): new model with a `patient` FK to `AddPatient`, whatever fields the tab needs, and — if both patient and physio can write to it — a nullable provenance field:
   ```python
   recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
   ```
   `recorded_by=None` means the patient entered it themselves; set means a physio did. Run `makemigrations personal_account` then `migrate`.

2. **`patient_app/views.py`**:
   - Import the new model at the top.
   - In `_medical_profile_context(patient)`: query the entries, group/shape them as the tab needs, add a `*_count` for the tab-card badge, return both in the context dict.
   - In `_attach_medical_profile_urls(context, patient, is_physio)`: add an `*_add_url` in both the `is_physio` and `else` branches (`reverse('physio-<thing>-add', kwargs=pid)` vs `reverse('patient-<thing>-add')`), and a `*_delete` lambda in both branches, then attach `.delete_url` to every entry in a loop at the bottom of the function.
   - Add patient-facing web views `patient_<thing>_add` / `patient_<thing>_delete` (session-based, `@patient_login_required`, mirror `patient_diet_add`/`patient_diet_delete`), redirecting to `f"{reverse('patient-medical-profile')}?tab=<thing>"`.
   - If the data should also be in the native-app JSON payload: extend `_medical_profile_dict` and add `patient_api_<thing>_add` / `patient_api_<thing>_delete` JSON views near the other `patient_api_*` endpoints.

3. **`patient_app/urls.py`**: add the web (`patient-<thing>/add/`, `patient-<thing>/<int:id>/delete/`) and, if applicable, JSON API (`api/medical-profile/<thing>/add/`, `.../<int:id>/delete/`) URL patterns.

4. **`detail_app/views.py`**: add `physio_<thing>_add` / `physio_<thing>_delete` (`@login_required`, `patient_id` in the URL, set `recorded_by=request.user` on create), mirroring `physio_diet_add`/`physio_diet_delete`. Redirect via the existing `_physio_tab_redirect(patient_id, '<thing>')` helper.

5. **`detail_app/urls.py`**: add `physio-<thing>-add` / `physio-<thing>-delete` URL patterns — required before step 2's `reverse()` calls will resolve.

6. **Template** (`patient-medical-profile.html`):
   - Add a tab-card `<button data-tab="<thing>">` to `.mp-tabs`, with an `.mp-tab-icon icon-<thing>` (give it a background color in the `<style>` block, same pattern as `icon-diet`/`icon-nursing`), Active/Inactive status from the count, and a count pill. Also add `data-count="{{ <thing>_count }}"` on the button itself (and for a dual-metric tab like Medicine's Rx-vs-medicine or Consultation's visit-vs-follow-up-due, the extra `data-*-count` attributes too) — the AJAX wiring below needs a starting count to increment/decrement client-side.
   - Add `<div class="mp-tab-panel mp-card" data-tab-panel="<thing>" hidden>` with the entries rendered via `.mp-tile-grid`/`.mp-tile` (showing `{% if entry.recorded_by %}Added by Dr. {{ entry.recorded_by.get_full_name|default:entry.recorded_by.username }}{% endif %}`) and an `.mp-add-form` posting to `*_add_url`. Give the `.mp-tile-grid` a `data-empty-text="..."` attribute matching its `{% empty %}` message (used to restore the empty-state after the last tile of that kind is deleted), and give each `.mp-tile` a `data-kind="<thing>"` attribute.
   - If grouping into columns (like Medication's time-of-day or Diet Chart's meal-time), build the grouped structure as a **list of `{key, label, entries}` dicts** in the view (not a raw dict), since Django templates can't do variable dict-key lookup without a custom filter.
   - **Add `data-ajax-kind="<thing>"` to the `<form class="mp-add-form">` itself** so the page's generic AJAX wiring (see below) picks it up automatically — this is now the default for every add-form on this page; only skip it for a genuinely rare, one-off action (e.g. Rx issuance, status-change buttons), not for anything a user might enter more than once in a sitting.

7. **AJAX add/delete, not a page reload per entry.** Every add-form avoids a full page reload on submit — important because a user logging many rows in one sitting (a dozen+ medicines, a week of diet entries) would otherwise eat one reload per row. The page's own JS (`<script>` block, search for "AJAX add / delete") handles this generically:
   - Every `form.mp-add-form[data-ajax-kind]` is wired automatically; its submit is intercepted, POSTed via `fetch` with an `X-Requested-With: XMLHttpRequest` header, and on success a tile is built **client-side** and inserted into the form's preceding `.mp-tile-grid` — the client already knows the display text (it's exactly what the user just typed or clicked from a suggestion), so the server only needs to hand back `{success, id, delete_url, recorded_by}`. If a tile shows something the user *didn't* type (e.g. Assessment's region label, derived from the matched reference object, not the search box), add it to the JSON response via `_ajax_add_response`'s `extra={...}` kwarg and read it off `data.<field>` in the tile builder — don't make the client guess.
   - Delete needs **no new view at all** beyond one line: each `*_delete` view already calls `_wants_json(request)` and returns `JsonResponse({'success': True})` before its normal redirect when the request is AJAX. Deletion is wired once, generically, via event delegation on `.mp-entry-del` — it works automatically for every tile on the page, including kinds that don't AJAX-ify adding (Rx, saved Exercises).
   - To add a new kind: write its entry in `TILE_BUILDERS` (how to build the tile's HTML from the submitted `FormData` + JSON response) and `TAB_BUMP` (how to update that tab's status/pill count) in the JS. Follow the existing entries — most kinds are a one-liner through the shared `mpTileHtml()` helper; only kinds with non-uniform tile markup (Consultation's follow-up badge) need a bespoke builder.
   - `_wants_json`/`_ajax_add_response` exist in **both** `patient_app/views.py` and `detail_app/views.py` (mirrored, not shared, since the two apps don't import from each other) — add the new view's AJAX branch in both.
   - Left as plain reloads, deliberately: Rx issuance, Rx status-change (Mark Completed/Discontinue), and the Allergies/Medical History/Nursing save forms — all infrequent, one-at-a-time actions, not the repeated-entry case this exists for.

8. **Verify**: `manage.py check`, then a `django.test.Client()`-based script covering patient web add/delete, physio web add/delete (check `recorded_by` gets set), JSON API add/delete if applicable, and the tab-card count/status rendering. Write output to a file rather than piping through `manage.py shell` interactively — substring checks can false-positive on CSS/JS/flash-message text. For the AJAX wiring specifically, a `Client()`-based test can't exercise it (it's browser-side `fetch`) — verify with a real browser (Playwright): add several entries in a row and confirm the URL never navigates, the tile/pill update client-side, and a follow-up full reload shows the server agrees with what the client displayed. Clean up any test fixtures afterward.

9. **Ship**: commit on a feature branch, merge `--no-ff` into `main`, push, delete the branch, and remind the user to deploy (migrate step only needed if a migration shipped).

## Adding a doctor-issued clinical record (Rx pattern — physio-only writes)

Some Medical Profile data isn't a patient self-report that either side can edit — it's an authoritative clinical action (a prescription, a referral, a clearance) that only a licensed professional should be able to create or change, with the patient getting read-only visibility. `Rx` (`personal_account/models.py`) — a doctor-issued digital prescription shown inside the existing Medicine tab — is the first example. Use this pattern instead of the dual-edit tab recipe above when that's the shape of the data; don't force everything into "both sides can add/delete."

What's different from the dual-edit pattern:

- **`issued_by`, not `recorded_by`**: still `on_delete=models.SET_NULL, null=True` at the DB level (so deleting a user account doesn't cascade-delete clinical history), but application logic always sets it on creation — there is no code path where a patient creates one, so it's never actually null in practice. No `if entry.recorded_by` branching in the template; it's always shown.
- **A real status lifecycle**: `status` choices (e.g. `active`/`completed`/`discontinued`) plus `start_date` + optional `duration_days`. Add `end_date`/`is_expired`/`effective_status` as model `@property`s that derive from those two fields rather than writing a scheduled job just to flip `status` to `completed` when time runs out — `effective_status` is what templates and JSON API responses display, the raw `status` field is what forms/physio actions write to.
- **No patient-facing add/delete/status views or URLs at all.** Only `detail_app/views.py` gets `physio_<thing>_add` / `physio_<thing>_status` (updates the status field, physio-only — mirror `physio_rx_status`) / `physio_<thing>_delete`, each `@login_required` with `patient_id` in the URL. `_attach_medical_profile_urls` only sets the add/status/delete URLs inside the `is_physio` branch; set the corresponding variables to `None` in the `else` branch (Rx: `rx_delete = rx_status_url = None`) since nothing references them there.
- **Template gating**: the issuance form AND the status-change/delete buttons are wrapped in `{% if editing_patient_id %}` so patients only ever see a read-only tile with a colored status badge (`.mp-rx-status-active/completed/discontinued` is the established class pattern — green/gray/red). Guard status-change buttons further on the record's own state (e.g. only show "Mark Completed"/"Discontinue" when `rx.status == 'active'`).
- **It doesn't need its own tab.** `Rx` lives as an extra section inside the *existing* Medicine tab panel, not a new 7th tab button — adding a doctor-issued record to data that's already on the page is a valid alternative to the "always add a new tab" recipe above. Decide per-feature which fits.

**"Upcoming event" computation** (used for Rx's "next dose"): when a record has a recurring daily schedule (a `time_of_day` slot), add a module-level helper next to `get_nepal_time()` in `personal_account/models.py` (see `get_upcoming_doses`) that: resolves each slot to a fixed clock time (`DOSE_SLOT_TIMES` dict), uses `get_nepal_time()` for "now" (never naive `datetime.now()` — this app is Nepal-only), rolls to tomorrow if today's slot time has passed, filters to `effective_status == 'active'` records, and returns soonest-first. Expose it two ways: folded into the full `_medical_profile_dict` JSON payload (`upcoming_doses` key) for the native app's general profile fetch, and as its own lightweight `patient_api_<thing>_upcoming` GET endpoint (`?hours=N` look-ahead window) for a dedicated "next dose" widget that shouldn't have to pull the whole profile. There is no cron job or push notification wired to this — it's a point-in-time query, same deliberate scope limit as the Consultation tab's follow-up-date badge above.

**Verify**: same `django.test.Client()` approach as the dual-edit recipe, but additionally check: (a) the patient view never renders the issuance form or status/delete buttons, (b) the physio view does, (c) `effective_status` auto-shows the right thing once a record expires even though the raw `status` field is untouched, (d) the upcoming-event helper both includes due records and excludes expired/inactive ones. Watch for the same CSS-substring false positive as `followup_due` — a status badge's own text (e.g. "Discontinued") will false-positive a naive `"Discontinue" in body` check meant to verify an *action button* is hidden; match the exact tag boundary (`">Discontinue<"`) instead.
