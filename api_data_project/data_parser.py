import pandas as pd

REQUIRED_FIELDS = {"id", "userId", "title", "body"}


def parse_posts(posts):
    if not isinstance(posts, list):
        raise ValueError("Expected a list of posts")

    valid_posts = []

    for post in posts:
        if not isinstance(post, dict):
            continue

        if not REQUIRED_FIELDS.issubset(post):
            continue

        if not all(
            isinstance(post[field], str) and post[field].strip()
            for field in ("title", "body")
        ):
            continue

        if not all(
            isinstance(post[field], int) and not isinstance(post[field], bool)
            and post[field] > 0
            for field in ("id", "userId")
        ):
            continue

        valid_posts.append({
            "id": post["id"],
            "userId": post["userId"],
            "title": post["title"].strip(),
            "body": post["body"].strip(),
        })

    return pd.DataFrame(
        valid_posts,
        columns=["id", "userId", "title", "body"]
    )