import logging
import os
import sys
import xml.etree.ElementTree as xml
from configparser import ConfigParser
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)

ignored_parents = ["sbforge-parent", "sbprojects-parent", "oss-parent"]

config = ConfigParser()
config.read("config.conf")
NEXUS_RELEASES_BASE_URL = config.get("nexus_crawl", "releases_base_url")
CRAWL_OUTPUT_DIR = config.get("nexus_crawl", "output_dir")
DIR_TRAVERSAL_BASE_DIR = config.get("dir_traversal", "base_dir")
DIR_TRAVERSAL_OUTPUT_DIR = config.get("dir_traversal", "output_dir")

ns = "http://maven.apache.org/POM/4.0.0"
xml.register_namespace('', ns)
tree = xml.ElementTree()

visited = set()


def __get_html(url):
    """ Make a GET request to the url and return the html content. """
    return requests.get(url).text


def __get_links_at_url(url):
    """ Generator returning links (href) from <a> tags at a given url one by one. """
    html = __get_html(url)
    soup = BeautifulSoup(html, 'html.parser')
    for link_tag in soup.find_all('a'):
        yield link_tag.get('href')


def __download_pom(url, destination_dir):
    """ Downloads the pom content at the given url and writes it to pom.xml under the given destination directory.
    The given url is expected to link directly to the content of a pom file, i.e.
    https://example-nexus.com/org/project/artifact-id/1.0.0/artifact_id-1.0.0.pom """
    print(destination_dir)
    pom_content = __get_html(url)
    Path(destination_dir).mkdir(parents=True, exist_ok=True)
    pom_path = os.path.join(destination_dir, "pom.xml")
    with open(pom_path, 'w+') as pom:
        pom.write(pom_content)


def __get_newest_pom(artifact_id_url, destination_dir):
    """ Given a nexus url at the artifact ID level, i.e. https://example-nexus.com/org/project/artifact-id,
    downloads the project's newest version pom to the specified destination dir. """
    versions = []

    for link_url in __get_links_at_url(artifact_id_url):
        if link_url != '../' and link_url.endswith('/'):
            versions.append(link_url)

    newest_version_url = sorted(versions, reverse=True)[0]

    for link_url in __get_links_at_url(newest_version_url):
        if link_url.endswith('.pom'):  # Only 1 should exist so just grab that
            __download_pom(link_url, destination_dir)
            # Pom-containing dir can contain .xml files and stuff, so doesn't hurt to skip checking them by breaking
            break


def __crawl_nexus(url, path):
    """ Recursively crawls nexus from the given url, building an equivalent folder structure to nexus from
    the provided path and downloading pom files to their respective project folders. """
    # logging.info(f'Crawling: {url}')
    for link_url in __get_links_at_url(url):
        # Need to check if folder contains version numbers and then just check latest.

        if link_url == '../':  # Don't go back
            continue
        elif link_url.endswith('/'):
            parent_url = os.path.dirname(link_url[:-1])
            if parent_url not in visited:
                # print(os.path.dirname(link_url), link_url)
                current_link_dir = os.path.basename(link_url[:-1])
                new_path = os.path.join(path, current_link_dir)
                __crawl_nexus(link_url, new_path)
            # else:
            #    print('Ignoring ' + link_url)
        elif link_url.endswith('.pom'):
            local_artifact_dir = os.path.dirname(path)

            version_url = os.path.dirname(link_url)
            artifact_id_url = os.path.dirname(version_url)
            visited.add(artifact_id_url)

            __get_newest_pom(artifact_id_url, local_artifact_dir)
            # Again pom-containing dir contains other stuff, but we're done now, so break
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Need arguments")
        sys.exit(1)

    if sys.argv[1] == "download":
        Path("releases").mkdir(exist_ok=True)
        nexus_url = "https://sbforge.org/nexus/content/repositories/releases"
        __crawl_nexus(nexus_url, 'releases')
