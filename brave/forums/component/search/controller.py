from __future__ import unicode_literals

import re

from bson import ObjectId

from web.auth import user
from web.core import Controller, HTTPMethod, url, request
from web.core.http import HTTPNotFound

from brave.forums.component.search.lib import search
from brave.forums.component.forum.model import Forum
from brave.forums.component.thread.model import Thread

class SearchController(Controller):
    def __init__(self, *args):
        pass

    def index(self, q=None):
        search_forums = [f.short for f in Forum.objects() if f.user_can_read(user)]
        results = search(q, search_forums)
        result_data = []
        for result in results:
            thread = Thread.objects(id=result['thread_id']).first()
            comment = thread.get_comment(ObjectId(result['comment_id']))
            result_data.append(dict(
                thread=thread,
                comment=comment,
            ))
        return 'brave.forums.template.search', dict(hits=result_data)
