from typing import Tuple, Dict

from django.urls import reverse

OBJ_PER_PAGE = 10


def get_urls_info(
        username: str, slug: str, post_id: int
) -> Tuple[Dict]:
    urls_templates_namespaces_kwargs = (
        {'namespace': 'posts:index',
         'template': 'posts/index.html',
         'kwargs': ''},
        {'namespace': 'posts:group_posts',
         'template': 'posts/group_list.html',
         'kwargs': {'slug': slug}},
        {'namespace': 'posts:profile',
         'template': 'posts/profile.html',
         'kwargs': {'username': username}},
        {'namespace': 'posts:post_detail',
         'template': 'posts/post_detail.html',
         'kwargs': {'post_id': post_id}},
        {'namespace': 'posts:post_edit',
         'template': 'posts/create_post.html',
         'kwargs': {'post_id': post_id}},
        {'namespace': 'posts:post_create',
         'template': 'posts/create_post.html',
         'kwargs': ''}
    )
    return urls_templates_namespaces_kwargs


def get_reversed_names(
        urls_templates_namespaces_kwargs: Tuple[Dict]
) -> Dict:
    reversed_pages_names = dict()
    for url in urls_templates_namespaces_kwargs:
        if url['kwargs']:
            reversed_pages_names.update({
                url['namespace']: reverse(
                    url['namespace'], kwargs=url['kwargs'])
            }
            )
        else:
            reversed_pages_names.update({
                url['namespace']: reverse(url['namespace'])}
            )
    return reversed_pages_names
