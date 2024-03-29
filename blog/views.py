from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404
from SuperBlog.secret import mail
from .forms import EmailPostForm, CommentForm, SearchForm
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity


# class PostListView(ListView):
#     queryset = Post.published.all()
#     context_object_name = 'posts'
#     paginate_by = 3
#     template_name = 'blog/post/list.html'


def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])
    paginator = Paginator(object_list, 3)
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    return render(request, 'blog/post/list.html', {'page': page, 'posts': posts, 'tag': tag})


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post, status='published', publish__year=year, publish__month=month,
                             publish__day=day)
    comments = post.comments.filter(active=True)
    if request.method == 'POST':  # komentarz zostal opublikowany
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)  # utworzenie obieku Comment
            new_comment.post = post  # przypisanie komentarza do biezacego posta
            new_comment.save()  # zapisanie komentarza w bazie danych
    else:
        comment_form = CommentForm()
    post_tags_ids = post.tags.values_list('id', flat=True)
    similiar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similiar_posts = similiar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]

    return render(request, 'blog/post/detail.html',
                  {'post': post, 'comments': comments, 'comment_form': comment_form, 'similiar_posts': similiar_posts})


def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False

    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = '{} ({}) zachęca do przeczytania "{}"'.format(cd['name'], cd['email'], post.title)
            message = 'Przeczytaj post "{}" na stronie {}\n\n Komentarz dodany przez {}: {}'.format(post.title,
                                                                                                    post_url,
                                                                                                    cd['name'],
                                                                                                    cd['comments'])
            send_mail(subject, message, mail, [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post, 'form': form, 'sent': sent})


def post_search(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            # search_vector = SearchVector('title', weight='A') + SearchVector('body', weight='B')
            # search_query = SearchQuery(query)
            results = Post.published.annotate(similarity=TrigramSimilarity('title',query)+TrigramSimilarity('body',query),).filter(similarity__gte=0.1).order_by('-similarity')
            # results = Post.objects.annotate(rank=SearchRank(search_vector, search_query)).filter(rank__gte=0.1).order_by('-rank')
    return render(request, 'blog/post/search.html', {'form': form, 'query': query, 'results': results})
