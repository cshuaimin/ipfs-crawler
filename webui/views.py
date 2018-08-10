from django.shortcuts import render, redirect
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

from .models import Html


def index(request):
    return render(request, 'webui/index.html')


def search(request):
    q = request.GET.get('q')
    if not q:
        return redirect('/')
    vector = SearchVector('filename', weight='A') + SearchVector('title', weight='B') + SearchVector('text', weight='C')
    query = SearchQuery(q)
    result = Html.objects.annotate(rank=SearchRank(vector, query)).order_by('rank')
    print(repr(result))
    return render(request, 'webui/results.html', {'result': result})