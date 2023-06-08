from base import Crawler
from settings import CONFIG
from toronites import Toronites

crawler = Crawler()

links = [
    "https://tinyzonetv.xyz/tv/demon-slayer-kimetsu-no-yaiba-42177",
    "https://tinyzonetv.xyz/tv/barracuda-queens-97345",
]


def crawl_film_via_link(href: str):
    slug = href.split("/")[-1]

    film_data, episodes_data = crawler.crawl_film(
        title="",
        slug=slug,
        fd_infor="",
        quality="HD",  # Edit if needed
        cover_src="",
        href=href,
        post_type=CONFIG.TYPE_TV_SHOWS,  # or CONFIG.TYPE_MOVIE
    )

    Toronites(film=film_data, episodes=episodes_data).insert_film()


def main():
    for link in links:
        crawl_film_via_link(href=link)


if __name__ == "__main__":
    main()
