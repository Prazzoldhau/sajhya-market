from django.shortcuts import render
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from .models import APKRelease


@staff_member_required
@csrf_exempt
def upload_apk(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    uploaded_file = request.FILES.get('apkFile')
    version = request.POST.get('version', '').strip()

    if not uploaded_file:
        return JsonResponse({'error': 'No file provided.'}, status=400)

    if not version:
        return JsonResponse({'error': 'Version is required (e.g. 1.2.0).'}, status=400)

    if not uploaded_file.name.endswith('.apk'):
        return JsonResponse({'error': 'File must have .apk extension.'}, status=400)

    if uploaded_file.size > 200 * 1024 * 1024:
        return JsonResponse({'error': 'File exceeds 200MB limit.'}, status=400)

    release_notes = request.POST.get('release_notes', '').strip()

    release = APKRelease.objects.create(
        version=version,
        file=uploaded_file,
        is_latest=True,
        release_notes=release_notes,
    )

    return JsonResponse({
        'success': True,
        'message': f'APK v{version} uploaded and marked as latest.',
        'version': version,
        'file': release.file.name,
    }, status=201)


@staff_member_required
def upload_page(request):
    releases = APKRelease.objects.all()[:10]
    return render(request, 'upload.html', {'releases': releases})


def latest_version_api(request):
    """Android app calls this to check if an update is available."""
    try:
        latest = APKRelease.objects.get(is_latest=True)
    except APKRelease.DoesNotExist:
        return JsonResponse({'available': False}, status=404)

    download_url = request.build_absolute_uri(f'/upload-app/download-apk/')
    return JsonResponse({
        'available': True,
        'version': latest.version,
        'download_url': download_url,
        'release_notes': latest.release_notes,
        'uploaded_at': latest.uploaded_at.isoformat(),
    })


def app_download_page(request):
    try:
        latest = APKRelease.objects.get(is_latest=True)
        context = {'file_exists': True, 'version': latest.version, 'release_notes': latest.release_notes}
    except APKRelease.DoesNotExist:
        context = {'file_exists': False, 'version': None}
    return render(request, 'download.html', context)


def download_latest_app(request):
    try:
        latest = APKRelease.objects.get(is_latest=True)
    except APKRelease.DoesNotExist:
        raise Http404("No APK available.")

    file_path = latest.file.path
    response = FileResponse(open(file_path, 'rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="sajhya-v{latest.version}.apk"'
    return response
