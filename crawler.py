import os
import requests
from bs4 import BeautifulSoup
import logging
from pathlib import Path

logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)


def get_html(url):
    return requests.get(url).text


def get_links_at_url(url):
    html = get_html(url)
    soup = BeautifulSoup(html, 'html.parser')
    for link_tag in soup.find_all('a'):
        yield link_tag.get('href')


def download_pom(url, destination_dir):
    pom_content = get_html(url)
    Path(destination_dir).mkdir(parents=True)  # exist_ok=True?
    with open(destination_dir + '/pom.xml', 'w+') as pom:
        pom.write(pom_content)


visited = set()


def get_newest_pom(repo_dir_url, destination_dir):
    versions = []

    for link_url in get_links_at_url(repo_dir_url):
        if link_url != '../' and link_url.endswith('/'):
            versions.append(link_url)

    newest_version_url = sorted(versions, reverse=True)[0]

    for link_url in get_links_at_url(newest_version_url):
        if link_url.endswith('.pom'):  # Only 1 should exist so just grab that
            print('downloading ' + link_url + ' to ' + destination_dir)
            # download_pom(link_url, destination_dir)
            # Pom-containing dir can contain .xml files and stuff, so doesn't hurt to skip checking them by breaking
            break


def crawl_nexus(url, path):
    # logging.info(f'Crawling: {url}')
    for link_url in get_links_at_url(url):
        # Need to check if folder contains version numbers and then just check latest.

        if link_url == '../':  # Don't go back
            continue
        elif link_url.endswith('/'):  # and os.path.dirname(link_url) not in visited:
            parent_url = os.path.dirname(link_url[:-1])
            if parent_url not in visited:
                # print(os.path.dirname(link_url), link_url)
                new_path = path + '/' + os.path.basename(link_url[:-1])
                crawl_nexus(link_url, new_path)
            # else:
            #    print('Ignoring ' + link_url)
        elif link_url.endswith('.pom'):
            local_repo_dir = os.path.dirname(path)

            version_url = os.path.dirname(link_url)
            repo_dir_url = os.path.dirname(version_url)
            visited.add(repo_dir_url)

            get_newest_pom(repo_dir_url, local_repo_dir)
            # Again pom-containing dir contains other stuff, but we're done now, so break
            break


crawl_nexus("https://sbforge.org/nexus/content/repositories/releases",
            os.getcwd())  # Should use some configurable path instead of cwd
