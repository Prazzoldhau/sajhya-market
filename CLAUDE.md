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
   - Add a tab-card `<button data-tab="<thing>">` to `.mp-tabs`, with an `.mp-tab-icon icon-<thing>` (give it a background color in the `<style>` block, same pattern as `icon-diet`/`icon-nursing`), Active/Inactive status from the count, and a count pill.
   - Add `<div class="mp-tab-panel mp-card" data-tab-panel="<thing>" hidden>` with the entries rendered via `.mp-tile-grid`/`.mp-tile` (showing `{% if entry.recorded_by %}Added by Dr. {{ entry.recorded_by.get_full_name|default:entry.recorded_by.username }}{% endif %}`) and an `.mp-add-form` posting to `*_add_url`.
   - If grouping into columns (like Medication's time-of-day or Diet Chart's meal-time), build the grouped structure as a **list of `{key, label, entries}` dicts** in the view (not a raw dict), since Django templates can't do variable dict-key lookup without a custom filter.

7. **Verify**: `manage.py check`, then a `django.test.Client()`-based script covering patient web add/delete, physio web add/delete (check `recorded_by` gets set), JSON API add/delete if applicable, and the tab-card count/status rendering. Write output to a file rather than piping through `manage.py shell` interactively — substring checks can false-positive on CSS/JS/flash-message text. Clean up any test fixtures afterward.

8. **Ship**: commit on a feature branch, merge `--no-ff` into `main`, push, delete the branch, and remind the user to deploy (migrate step only needed if a migration shipped).
