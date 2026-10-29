from api_client import fetch_posts
from data_parser import parse_posts


def main():
    posts = fetch_posts()
    df = parse_posts(posts)

    print(f"Valid posts: {len(df)}")
    print(df.head())


if __name__ == "__main__":
    main()