import logging
import os
import shutil
import subprocess
import xml.etree.ElementTree as xml
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from configparser import ConfigParser

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
    print(destination_dir)
    pom_content = get_html(url)
    Path(destination_dir).mkdir(parents=True, exist_ok=True)
    with open(destination_dir + '/pom.xml', 'w+') as pom:
        pom.write(pom_content)


def get_newest_pom(artifact_id_url, destination_dir):
    versions = []

    for link_url in get_links_at_url(artifact_id_url):
        if link_url != '../' and link_url.endswith('/'):
            versions.append(link_url)

    newest_version_url = sorted(versions, reverse=True)[0]

    for link_url in get_links_at_url(newest_version_url):
        if link_url.endswith('.pom'):  # Only 1 should exist so just grab that
            # print('downloading ' + link_url + ' to ' + destination_dir)
            if artifact_id_url.endswith('-parent'):
                print('artifact: ' + destination_dir + ' parent: ', end='')
                download_pom(link_url, os.path.dirname(destination_dir))
            download_pom(link_url, destination_dir)
            # Pom-containing dir can contain .xml files and stuff, so doesn't hurt to skip checking them by breaking
            break


visited = set()


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
            local_artifact_dir = os.path.dirname(path)

            version_url = os.path.dirname(link_url)
            artifact_id_url = os.path.dirname(version_url)
            visited.add(artifact_id_url)

            get_newest_pom(artifact_id_url, local_artifact_dir)
            # Again pom-containing dir contains other stuff, but we're done now, so break
            break


def run_dependency_tree(output_path):
    command = ['mvn', 'dependency:tree', '-DoutputFile=' + output_path, '-DoutputType=tgf']
    try:
        process_output = subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        print('>>>>> ERROR <<<<<')
        print(e.output)


def find_parent_dirs_and_move_children(root_dir):
    move_dict = defaultdict(list)

    for root_path, dirs, files in os.walk(root_dir):
        for dir_name in dirs:
            parent_dir = os.path.basename(root_path)
            if dir_name == parent_dir:
                other_dirs = [d for d in dirs if d != dir_name]
                for other_dir in other_dirs:
                    parent_path = os.path.join(root_path, dir_name)
                    child_path = os.path.join(root_path, other_dir)
                    move_dict[parent_path].append(child_path)
            elif dir_name.endswith('-parent'):
                project_prefix = dir_name.replace('-parent', '')
                other_dirs = [d for d in dirs if d != dir_name and d.startswith(project_prefix)]
                for other_dir in other_dirs:
                    parent_path = os.path.join(root_path, dir_name)
                    child_path = os.path.join(root_path, other_dir)
                    move_dict[parent_path].append(child_path)

    for parent_path, child_paths in move_dict.items():
        for child_path in child_paths:
            child_basename = os.path.basename(child_path)
            new_child_path = os.path.join(parent_path, child_basename)
            # print('moving ' + child_path + ' to ' + new_child_path)
            os.rename(child_path, new_child_path)


def pom_parent_finder(path):
    ns = "http://maven.apache.org/POM/4.0.0"
    xml.register_namespace('', ns)
    tree = xml.ElementTree()
    tree.parse(path)
    artifact_id = tree.find("{%s}artifactId" % ns)
    ignored_parents = ["sbforge-parent", "sbprojects-parent"]

    parent_artifact_id = None
    for elem in tree.getroot().findall("{%s}parent" % ns):
        parent_artifact_id = elem.find("{%s}artifactId" % ns)

    if parent_artifact_id is None or parent_artifact_id.text in ignored_parents:
        move_parent_pom(path, artifact_id)


def move_parent_pom(pom_path, artifact_id):
    Path("new_releases").mkdir(exist_ok=True)
    old_path = pom_path
    pom_path = pom_path.strip("/pom.xml")
    pom_path = pom_path.rsplit("/", 1)[0]
    pom_path = pom_path.split("releases/", 1)[-1]

    artifact_id = artifact_id.text.rsplit("-parent", 1)[0] + "-parent"

    full_path_string = "new_releases/" + pom_path + "/" + artifact_id
    Path(full_path_string).mkdir(parents=True, exist_ok=True)

    shutil.move(old_path, full_path_string)
    print("Moved pom to parent folder: " + full_path_string)


# find_parent_dirs_and_move_children("releases")

# if __name__ == '__main__':
#     conf = ConfigParser()
#     conf.read('config.conf')
#     nexus_url = conf.get('crawl', 'base_url')
#     output_dir = conf.get('crawl', 'output_dir')
#     crawl_nexus(nexus_url, output_dir)
#     find_parent_dirs_and_move_children('releases')

pom_parent_finder('releases/netarchive/archive/pom.xml')
