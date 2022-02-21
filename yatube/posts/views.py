from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView

from .forms import CommentForm, PostForm
from .models import Group, Post, User, Follow, Comment
from .utils import OBJ_PER_PAGE


class Index(ListView):
    template_name = 'posts/index.html'
    paginate_by = OBJ_PER_PAGE
    model = Post

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['index'] = True
        return context


class GroupPosts(ListView):
    template_name = 'posts/group_list.html'
    paginate_by = OBJ_PER_PAGE

    def get_group(self, **kwargs):
        slug = self.kwargs['slug']
        group = get_object_or_404(Group, slug=slug)
        return group

    def get_queryset(self, **kwargs):
        group = self.get_group(**kwargs)
        post_list = group.posts.select_related('author')
        return post_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        group = self.get_group(**kwargs)
        context['group'] = group
        return context


class Profile(ListView):
    template_name = 'posts/profile.html'
    paginate_by = OBJ_PER_PAGE

    def get_author(self, **kwargs):
        username = self.kwargs['username']
        author = get_object_or_404(User, username=username)
        return author

    def get_queryset(self, **kwargs):
        author = self.get_author(**kwargs)
        post_list = author.posts.select_related('group')
        return post_list

    def get_context_data(self, **kwargs):
        author = self.get_author(**kwargs)
        context = super().get_context_data()
        following = False
        if self.request.user.is_authenticated:
            following = Follow.objects.filter(
                user=self.request.user,
                author=author
            ).exists()
        context['author'] = author
        context['following'] = following
        context['is_not_author'] = self.request.user != author
        return context


class PostDetailView(DetailView):
    template_name = 'posts/post_detail.html'
    model = Post
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        post = self.get_object()
        author = post.author

        author_posts_count = author.posts.count()
        is_author_of_post = author == self.request.user

        form = CommentForm(self.request.POST or None)
        comments = post.comments.select_related('author')

        context = super().get_context_data()
        context['post'] = post
        context['author_posts_count'] = author_posts_count
        context['is_author_of_post'] = is_author_of_post
        context['form'] = form
        context['comments'] = comments
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    template_name = 'posts/create_post.html'
    model = Post
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'posts:profile',
            kwargs={'username': self.request.user}
        )


class PostEditView(LoginRequiredMixin, UpdateView):
    template_name = 'posts/create_post.html'
    model = Post
    pk_url_kwarg = 'post_id'
    form_class = PostForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.request.user != self.object.author:
            return redirect('posts:post_detail', post_id=self.object.id)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        context['post_id'] = self.object.id
        return context

    def get_success_url(self):
        return reverse('posts:post_detail', kwargs={'post_id': self.object.id})


class AddComment(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    pk_url_kwarg = 'post_id'

    def form_valid(self, form):
        post_id = self.kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        form.instance.author = self.request.user
        form.instance.post = post
        return super().form_valid(form)

    def get_success_url(self):
        post_id = self.kwargs.get('post_id')
        return reverse('posts:post_detail', kwargs={'post_id': post_id})


class FollowIndex(LoginRequiredMixin, ListView):
    template_name = 'posts/follow.html'
    paginate_by = OBJ_PER_PAGE

    def get_queryset(self):
        user = self.request.user
        post_list = Post.objects.filter(author__following__user=user)
        return post_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['follow'] = True
        return context


class ProfileFollow(LoginRequiredMixin, View):
    def get(self, request, username):
        user = request.user
        author = get_object_or_404(User, username=username)
        if user != author:
            Follow.objects.get_or_create(user=user, author=author)
        return redirect('posts:profile', username)


class ProfileUnfollow(LoginRequiredMixin, View):
    def get(self, request, username):
        user = request.user
        author = get_object_or_404(User, username=username)
        Follow.objects.filter(user=user, author=author).delete()
        return redirect('posts:profile', username)
