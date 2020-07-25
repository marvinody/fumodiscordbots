import requests
import json

GRAPHQL_URL = "https://www.instagram.com/graphql/query/"
TIMELINE_QUERY_HASH = "e769aa130647d2354c40ea6a439bfc08"


class Timeline:
    def __init__(self, *args, **kwargs):
        self.posts = kwargs['posts']
        self.hasNextPage = kwargs['hasNextPage']

    @staticmethod
    def FromGraphQL(response):
        media = response['data']['user']['edge_owner_to_timeline_media']
        edges = media['edges']
        posts = [TimelineEntry.FromGraphQL(edge) for edge in edges]
        return Timeline(
            hasNextPage=media['page_info']['has_next_page'],
            posts=posts,
        )


class TimelineEntry:
    def __init__(self, *args, **kwargs):
        self.id = kwargs['id']
        self.width = kwargs['width']
        self.height = kwargs['height']
        self.displayURL = kwargs['displayURL']
        self.isVideo = kwargs['isVideo']
        self.caption = kwargs['caption']
        self.shortcode = kwargs['shortcode']

    @staticmethod
    def FromGraphQL(edge):
        node = edge['node']
        caption = node['edge_media_to_caption']['edges'][0]['node'][
            'text'] if node['edge_media_to_caption']['edges'] else None
        return TimelineEntry(id=node['id'],
                             width=node['dimensions']['width'],
                             height=node['dimensions']['height'],
                             displayURL=node['display_url'],
                             isVideo=node['is_video'],
                             caption=caption,
                             shortcode=node['shortcode'])


def fetchTimeline(userId):
    req = requests.get(
        GRAPHQL_URL, {
            "query_hash": TIMELINE_QUERY_HASH,
            "variables": json.dumps({
                "id": userId,
                "after": "",
                "first": 12,
            })
        })
    timeline = Timeline.FromGraphQL(req.json())
    return timeline
