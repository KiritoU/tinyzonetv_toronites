import base64
import logging
import os
import re
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from time import sleep

import requests
from phpserialize import serialize
from slugify import slugify

from _db import database
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class ToronitesHelper:
    def get_header(self):
        header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E150",  # noqa: E501
            "Accept-Encoding": "gzip, deflate",
            # "Cookie": CONFIG.COOKIE,
            "Cache-Control": "max-age=0",
            "Accept-Language": "vi-VN",
            "Referer": "https://french-anime.com/",
        }
        return header

    def download_url(self, url):
        return requests.get(url, headers=self.get_header())

    def save_thumb(
        self,
        image_url: str,
        title: str = "",
        overwrite: bool = False,
    ) -> str:
        image_ext = image_url.split(".")[-1]
        Path(CONFIG.COVER_SAVE_FOLDER).mkdir(parents=True, exist_ok=True)

        thumb_image_name = f"{slugify(title)}.{image_ext}"
        save_thumb_image_path = os.path.join(CONFIG.COVER_SAVE_FOLDER, thumb_image_name)
        is_not_saved = not Path(save_thumb_image_path).is_file()
        if overwrite or is_not_saved:
            image = self.download_url(image_url)
            with open(save_thumb_image_path, "wb") as f:
                f.write(image.content)
            is_not_saved = True

        return [os.path.join("cover", thumb_image_name), is_not_saved]

    def generate_trglinks(
        self,
        server: str,
        link: str,
        lang: str = "English",
        quality: str = "HD",
    ) -> str:
        if "http" not in link:
            link = "https:" + link

        server_term_id, isNewServer = self.insert_terms(
            post_id=0, terms=server, taxonomy="server"
        )

        lang_term_id, isNewLang = self.insert_terms(
            post_id=0, terms=lang, taxonomy="language"
        )

        quality_term_id, isNewQuality = self.insert_terms(
            post_id=0, terms=quality, taxonomy="quality"
        )

        link_data = {
            "type": "1",
            "server": str(server_term_id),
            "lang": int(lang_term_id),
            "quality": int(quality_term_id),
            "link": base64.b64encode(bytes(escape(link), "utf-8")).decode("utf-8"),
            "date": self.get_timeupdate().strftime("%d/%m/%Y"),
        }
        link_data_serialized = serialize(link_data).decode("utf-8")

        return f's:{len(link_data_serialized)}:"{link_data_serialized}";'

    def format_text(self, text: str) -> str:
        return text.strip("\n").replace('"', "'").strip()

    def convert_to_minutes(self, time_str):
        try:
            # Extract hours and minutes from the string using regex
            hours = 0
            minutes = 0
            match = re.findall(r"\d+", time_str)
            if len(match) > 0:
                if "h" in time_str:
                    hours = int(match[0])
                if "m" in time_str:
                    minutes = int(match[-1])
            # Convert hours to minutes and add to minutes
            total_minutes = hours * 60 + minutes
            return str(total_minutes)
        except:
            return "0"

    def error_log(self, msg: str, log_file: str = "failed.log"):
        datetime_msg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        Path("log").mkdir(parents=True, exist_ok=True)
        with open(f"log/{log_file}", "a") as f:
            print(f"{datetime_msg} LOG:  {msg}\n{'-' * 80}", file=f)

    def get_saison_for_title(self, season_str: str) -> int:
        season_str = season_str.replace("\n", " ").lower()
        regex = re.compile(r"saison\s+(\d+)")
        match = regex.search(season_str)
        if match:
            saison_for_title = " - Saison " + match.group(1)
        else:
            saison_for_title = ""

        return saison_for_title

    def get_season_number(self, season_str: str) -> str:
        season_str = season_str.replace("\n", " ").lower()
        regex = re.compile(r"season\s+(\d+)")
        match = regex.search(season_str)
        if match:
            return match.group(1)
        else:
            return "1"

    def get_episode_title_and_language_and_number(self, episode_title: str) -> str:
        title = episode_title.lower()

        if title.endswith("en vf"):
            language = "VF"
            title = title.replace("en vf", "").strip()

        elif title.endswith("en vostfr"):
            language = "VOSTFR"
            title = title.replace("en vostfr", "").strip()
        else:
            language = "VO"

        pattern = r"épisode\s(\d+(\.\d+)?)"
        match = re.search(pattern, title)
        if match:
            number = match.group(1)
        else:
            self.error_log(
                msg=f"Unknown episode number for: {title}",
                log_file="toroplay_get_episode_title_and_language_and_number.log",
            )
            number = ""

        title = title.title()

        return [title, language, number]

    def get_title_and_season_number(self, title: str) -> list:
        title = title
        season_number = "1"

        return [
            self.format_text(title),
            self.get_season_number(self.format_text(season_number)),
        ]

    def insert_postmeta(self, postmeta_data: list, table: str = "postmeta"):
        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}{table}", data=postmeta_data, is_bulk=True
        )

    def generate_film_data(
        self,
        title,
        slug,
        description,
        post_type,
        trailer_id,
        cover_src,
        extra_info,
    ):
        post_data = {
            "description": description,
            "title": title,
            "slug": slug,
            "post_type": post_type,
            # "id": "202302",
            "youtube_id": f"{trailer_id}",
            # "serie_vote_average": extra_info["IMDb"],
            # "episode_run_time": extra_info["Duration"],
            "fondo_player": cover_src,
            "poster_url": cover_src,
            "cover_src": cover_src,
            # "category": extra_info["Genre"],
            # "stars": extra_info["Actor"],
            # "director": extra_info["Director"],
            # "release-year": [extra_info["Release"]],
            # "country": extra_info["Country"],
        }

        key_mapping = {
            "IMDB": "rating",
            "Released": "annee",
            "Genre": "category",
            "Casts": "cast",
            # "Duration": "field_runtime",
            "Country": "country",
            "Production": "directors",
            "quality": "quality",
        }

        for info_key in key_mapping.keys():
            if info_key in extra_info.keys():
                post_data[key_mapping[info_key]] = extra_info[info_key]

        for info_key in ["cast", "directors"]:
            if info_key in post_data.keys():
                post_data[f"{info_key}_tv"] = post_data[info_key]
        # post_data["field_runtime"] = post_data.get("field_runtime", "").replace(
        #     "m", " min"
        # )

        return post_data

    def get_timeupdate(self) -> datetime:
        timeupdate = datetime.now() - timedelta(hours=7)

        return timeupdate

    def generate_post(self, post_data: dict) -> tuple:
        timeupdate = self.get_timeupdate()
        data = (
            0,
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            post_data["description"],
            post_data["title"],
            "",
            "publish",
            "open",
            "open",
            "",
            post_data["slug"],
            "",
            "",
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            "",
            0,
            "",
            0,
            post_data["post_type"],
            "",
            0,
        )
        return data

    def insert_post(self, post_data: dict) -> int:
        data = self.generate_post(post_data)
        post_id = database.insert_into(table=f"{CONFIG.TABLE_PREFIX}posts", data=data)
        return post_id

    def insert_thumb(self, post_data: dict):
        thumb_insert_data, _ = helper.save_thumb(
            post_data.get("poster_url"), post_data.get("title")
        )

        thumb_name = thumb_insert_data.split("/")[-1]
        timeupdate = self.get_timeupdate()
        thumb_post_data = (
            0,
            timeupdate,
            timeupdate,
            "",
            thumb_name,
            "",
            "inherit",
            "open",
            "closed",
            "",
            thumb_name,
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            "attachment",
            "image/png",
            0,
            # "",
        )

        thumb_id = database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}posts", data=thumb_post_data
        )
        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            data=(thumb_id, "_wp_attached_file", thumb_insert_data),
        )

        return thumb_id

    def insert_film(self, post_data: dict) -> int:
        post_id = self.insert_post(post_data)
        timeupdate = self.get_timeupdate()

        postmeta_data = [
            (post_id, "_edit_last", "1"),
            (post_id, "_edit_lock", f"{int(timeupdate.timestamp())}:1"),
            # _thumbnail_id
            (post_id, "tr_post_type", "2"),
            (
                post_id,
                "field_title",
                post_data.get("field_title", post_data.get("title")),
            ),
            (
                post_id,
                "poster_hotlink",
                post_data["poster_url"],
            ),
            (
                post_id,
                "backdrop_hotlink",
                post_data["fondo_player"],
            ),
        ]

        if CONFIG.DOWNLOAD_COVER:
            thumb_id = self.insert_thumb(post_data)
            postmeta_data.append(
                (post_id, "_thumbnail_id", thumb_id),
            )

        if CONFIG.IS_TRAILER_NEEDED and post_data["youtube_id"]:
            postmeta_data.append(
                (
                    post_id,
                    "field_trailer",
                    CONFIG.YOUTUBE_IFRAME.format(post_data["youtube_id"]),
                )
            ),

        if "rating" in post_data.keys():
            postmeta_data.append((post_id, "rating", post_data["rating"]))

        tvseries_postmeta_data = [
            (
                post_id,
                "number_of_seasons",
                "0",
            ),
            (
                post_id,
                "number_of_episodes",
                "0",
            ),
        ]
        movie_postmeta_data = []

        if "annee" in post_data.keys():
            annee = (
                post_id,
                "field_date",
                post_data["annee"].strip(),
            )

            tvseries_postmeta_data.append(annee)
            movie_postmeta_data.append(annee)

        if "field_runtime" in post_data.keys():
            tvseries_postmeta_data.append(
                (
                    post_id,
                    "field_runtime",
                    "a:1:{i:0;s:"
                    + str(len(post_data["field_runtime"]))
                    + ':"'
                    + str(post_data["field_runtime"])
                    + '";}',
                )
            )

            movie_postmeta_data.append(
                (post_id, "field_runtime", f"{post_data['field_runtime']}"),
            )

        if post_data["post_type"] == CONFIG.TYPE_TV_SHOWS:
            postmeta_data.extend(tvseries_postmeta_data)
        else:
            postmeta_data.extend(movie_postmeta_data)

        self.insert_postmeta(postmeta_data)

        for taxonomy in CONFIG.TAXONOMIES[post_data["post_type"]]:
            if taxonomy in post_data.keys() and post_data[taxonomy]:
                self.insert_terms(
                    post_id=post_id, terms=post_data[taxonomy], taxonomy=taxonomy
                )

        return post_id

    def format_condition_str(self, equal_condition: str) -> str:
        return equal_condition.replace("\n", "").strip().lower()

    def insert_terms(
        self,
        post_id: int,
        terms: str,
        taxonomy: str,
        is_title: str = False,
        term_slug: str = "",
    ):
        try:
            terms = (
                [term.strip() for term in terms.split(",")] if not is_title else [terms]
            )
        except Exception as e:
            print(e)
        termIds = []
        for term in terms:
            term_insert_slug = slugify(term_slug) if term_slug else slugify(term)
            cols = "tt.term_taxonomy_id, tt.term_id"
            table = (
                f"{CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t"
            )
            condition = f't.slug = "{term_insert_slug}" AND tt.term_id=t.term_id AND tt.taxonomy="{taxonomy}"'

            be_term = database.select_all_from(
                table=table, condition=condition, cols=cols
            )
            if not be_term:
                term_id = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}terms",
                    data=(term, term_insert_slug, 0),
                )
                term_taxonomy_count = 1 if taxonomy == "seasons" else 0
                term_taxonomy_id = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_taxonomy",
                    data=(term_id, taxonomy, "", 0, term_taxonomy_count),
                )
                termIds = [term_taxonomy_id, True]
            else:
                term_taxonomy_id = be_term[0][0]
                term_id = be_term[0][1]
                termIds = [term_taxonomy_id, False]

            try:
                database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_relationships",
                    data=(post_id, term_taxonomy_id, 0),
                )
            except:
                pass

        return termIds

    def get_server_name_from(self, link: str) -> str:
        server_name = ""
        result = re.search(r"(?<=//)(.*?)(?=/)", link)
        if result:
            server_name = result.group(1)

        return server_name


helper = ToronitesHelper()


class Toronites:
    def __init__(self, film: dict, episodes: dict, season_str: str = ""):
        self.film = film
        self.film["quality"] = self.film["extra_info"].get("quality", "HD")
        self.film["version"] = "English"
        self.episode = {}
        self.episodes = episodes
        self.season_str = season_str

    def insert_movie_details(self, post_id):
        if not self.episodes:
            return

        logging.info("Inserting movie players")

        quality = self.film["quality"]
        len_episode_links = 0
        postmeta_data = []

        movie_links = [
            f"https://www.2embed.to/embed/tmdb/movie?id={self.episodes.get('tmdb_id', '0')}"
        ]
        for link in movie_links:
            if link:
                postmeta_data.append(
                    (
                        post_id,
                        f"trglinks_{len_episode_links}",
                        helper.generate_trglinks(
                            server=CONFIG.LINK_LANGUAGE,
                            link=link,
                            lang=quality,
                            quality=CONFIG.LINK_LANGUAGE,
                        ),
                    )
                )
                len_episode_links += 1

        postmeta_data.append((post_id, "trgrabber_tlinks", len_episode_links))
        helper.insert_postmeta(postmeta_data)

    def get_thumb_id_be(self, post_id):
        condition = f"post_id={post_id} AND meta_key='_thumbnail_id'"
        thumb_postmeta_thumb_id = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            condition=condition,
            cols="meta_value",
        )
        if thumb_postmeta_thumb_id:
            thumb_id = thumb_postmeta_thumb_id[0][0]

            self.film["cover_id"] = thumb_id
            return

        self.film["cover_id"] = "0"

    def insert_root_film(self) -> list:
        condition_post_name = self.film["slug"]
        condition = f"""post_name = '{condition_post_name}' AND post_type='{self.film["post_type"]}'"""
        be_post = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
        )
        if not be_post:
            logging.info(f'Inserting root film: {self.film["post_title"]}')
            post_data = helper.generate_film_data(
                self.film["post_title"],
                self.film["slug"],
                self.film["description"],
                self.film["post_type"],
                self.film["trailer_id"],
                self.film["cover_src"],
                self.film["extra_info"],
            )

            post_id, is_new_post_inserted = [helper.insert_film(post_data), True]
        else:
            post_id, is_new_post_inserted = [be_post[0][0], False]

        logging.info(f"Post ID: {post_id}")

        self.get_thumb_id_be(post_id)

        return post_id, is_new_post_inserted

    def update_meta_for_post_or_term(
        self, table, condition, new_meta_value, adding: bool = False
    ):
        try:
            be_meta_value = database.select_all_from(
                table=table,
                condition=condition,
                cols="meta_value",
            )[0][0]

            if adding:
                new_meta_value = str(int(new_meta_value) + int(be_meta_value))

            if int(be_meta_value) < int(new_meta_value):
                database.update_table(
                    table=table,
                    set_cond=f"meta_value={new_meta_value}",
                    where_cond=condition,
                )
        except Exception as e:
            helper.error_log(
                msg=f"Error while update_season_number_of_episodes\nSeason {condition} - Number of episodes {new_meta_value}\n{e}",
                log_file="torotheme.update_season_number_of_episodes.log",
            )

    def insert_episode(self, post_id: int, season_term_id: int, thumb_id: str = "0"):
        len_episodes = 0

        for episode_number, episode_title in self.episode.items():
            episode_title_self_created = (
                self.film["post_title"]
                + f" {self.film['season_number']}x{episode_number}"
            )
            episode_term_name = (
                episode_title if episode_title else episode_title_self_created
            )

            episode_term_slug = slugify(
                self.film["slug"] + f" {self.film['season_number']}x{episode_number}"
            )
            episode_term_id, is_new_episode = helper.insert_terms(
                post_id=post_id,
                terms=episode_term_name,
                taxonomy="episodes",
                is_title=True,
                term_slug=episode_term_slug,
            )

            if not is_new_episode:
                continue

            len_episode_links = 0
            logging.info(f"Inserting new Episode {episode_number}: {episode_title}")

            termmeta_data = [
                (episode_term_id, "episode_number", episode_number),
                (episode_term_id, "name", episode_title),
                (episode_term_id, "season_number", self.film["season_number"]),
                (episode_term_id, "tr_id_post", post_id),
            ]

            if thumb_id != "0":
                termmeta_data.append(
                    (episode_term_id, "still_path", thumb_id),
                )
            else:
                termmeta_data.append(
                    (episode_term_id, "still_path_hotlink", self.film["cover_src"]),
                )
            quality = self.film.get("quality", "HD")

            episode_links = [
                f"https://www.2embed.to/embed/tmdb/tv?id={self.episodes.get('tmdb_id', '0')}&s={self.film['season_number']}&e={episode_number}"
            ]
            for link in episode_links:
                if link:
                    termmeta_data.append(
                        (
                            episode_term_id,
                            f"trglinks_{len_episode_links}",
                            helper.generate_trglinks(
                                server=CONFIG.LINK_LANGUAGE,
                                link=link,
                                lang=quality,
                                quality=CONFIG.LINK_LANGUAGE,
                            ),
                        )
                    )
                    len_episode_links += 1

            termmeta_data.append(
                (episode_term_id, "trgrabber_tlinks", len_episode_links)
            )

            helper.insert_postmeta(termmeta_data, "termmeta")

            len_episodes += len_episode_links > 0

        table = f"{CONFIG.TABLE_PREFIX}termmeta"
        condition = f"term_id={season_term_id} AND meta_key='number_of_episodes'"
        self.update_meta_for_post_or_term(table, condition, len_episodes)

        table = f"{CONFIG.TABLE_PREFIX}postmeta"
        condition = f"post_id={post_id} AND meta_key='number_of_episodes'"
        self.update_meta_for_post_or_term(table, condition, len_episodes, adding=True)

    def insert_season(self, post_id: int):
        season_term_name = (
            self.film["post_title"] + " - Season " + self.film["season_number"]
        )
        season_term_slug = self.film["slug"] + " - " + self.film["season_number"]
        season_term_id, isNewSeason = helper.insert_terms(
            post_id=post_id,
            terms=season_term_name,
            taxonomy="seasons",
            is_title=True,
            term_slug=season_term_slug,
        )

        termmeta_data = [
            (season_term_id, "number_of_episodes", "0"),
            (season_term_id, "name", "Season " + self.film["season_number"]),
            (season_term_id, "overview", ""),
            (season_term_id, "tr_id_post", post_id),
            (season_term_id, "poster_path_hotlink", self.film["cover_src"]),
            (season_term_id, "season_number", self.film["season_number"]),
        ]

        if isNewSeason:
            logging.info(f"Inserted new season: {season_term_name}")
            helper.insert_postmeta(termmeta_data, "termmeta")

            table = f"{CONFIG.TABLE_PREFIX}postmeta"
            condition = f"post_id={post_id} AND meta_key='number_of_seasons'"
            self.update_meta_for_post_or_term(
                table, condition, self.film["season_number"]
            )

        return season_term_id

    def insert_film(self):
        self.film["post_title"] = self.film["title"]

        post_id, is_new_post_inserted = self.insert_root_film()

        if not post_id:
            return

        if self.film["post_type"] != CONFIG.TYPE_TV_SHOWS:
            if is_new_post_inserted:
                self.insert_movie_details(post_id)
            return

        for key, value in self.episodes.items():
            if "season" in key.lower():
                self.film["season_number"] = helper.get_season_number(key)
                self.episode = value
                season_term_id = self.insert_season(post_id)
                self.insert_episode(post_id, season_term_id, self.film["cover_id"])

        sleep(1)
