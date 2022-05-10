import logging
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as xml
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)

ns = "http://maven.apache.org/POM/4.0.0"
xml.register_namespace('', ns)
tree = xml.ElementTree()

visited = set()


def __get_html(url):
    return requests.get(url).text


def __get_links_at_url(url):
    html = __get_html(url)
    soup = BeautifulSoup(html, 'html.parser')
    for link_tag in soup.find_all('a'):
        yield link_tag.get('href')


def __download_pom(url, destination_dir):
    print(destination_dir)
    pom_content = __get_html(url)
    Path(destination_dir).mkdir(parents=True, exist_ok=True)
    with open(destination_dir + '/pom.xml', 'w+') as pom:
        pom.write(pom_content)


def __get_newest_pom(artifact_id_url, destination_dir):
    versions = []

    for link_url in __get_links_at_url(artifact_id_url):
        if link_url != '../' and link_url.endswith('/'):
            versions.append(link_url)

    newest_version_url = sorted(versions, reverse=True)[0]

    for link_url in __get_links_at_url(newest_version_url):
        if link_url.endswith('.pom'):  # Only 1 should exist so just grab that
            # print('downloading ' + link_url + ' to ' + destination_dir)
            if artifact_id_url.endswith('-parent'):
                print('artifact: ' + destination_dir + ' parent: ', end='')
                __download_pom(link_url, os.path.dirname(destination_dir))
            __download_pom(link_url, destination_dir)
            # Pom-containing dir can contain .xml files and stuff, so doesn't hurt to skip checking them by breaking
            break


def __crawl_nexus(url, path):
    # logging.info(f'Crawling: {url}')
    for link_url in __get_links_at_url(url):
        # Need to check if folder contains version numbers and then just check latest.

        if link_url == '../':  # Don't go back
            continue
        elif link_url.endswith('/'):  # and os.path.dirname(link_url) not in visited:
            parent_url = os.path.dirname(link_url[:-1])
            if parent_url not in visited:
                # print(os.path.dirname(link_url), link_url)
                new_path = path + '/' + os.path.basename(link_url[:-1])
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


def __run_dependency_tree(output_path):
    command = ['mvn', 'dependency:tree', '-DoutputFile=' + output_path, '-DoutputType=tgf']
    try:
        process_output = subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        print('>>>>> ERROR <<<<<')
        print(e.output)


def __pom_parent_finder(path):
    tree.parse(path)
    artifact_id = tree.find("{%s}artifactId" % ns)
    ignored_parents = ["sbforge-parent", "sbprojects-parent"]

    parent_artifact_id = None
    for elem in tree.getroot().findall("{%s}parent" % ns):
        parent_artifact_id = elem.find("{%s}artifactId" % ns)

    if parent_artifact_id is None or parent_artifact_id.text in ignored_parents:
        __move_parent_pom(path, artifact_id)


def __move_parent_pom(pom_path, artifact_id):
    Path("new_releases").mkdir(exist_ok=True)

    old_path = pom_path
    full_path_string = __create_pom_path(artifact_id, pom_path)
    Path(full_path_string).mkdir(parents=True, exist_ok=True)

    shutil.move(old_path, full_path_string + "/pom.xml")
    print("Moved pom to parent folder: " + full_path_string + "/pom.xml")


def __pom_child_finder(path):
    tree.parse(path)
    artifact_id = tree.find("{%s}artifactId" % ns)

    parent_artifact_id = None
    for elem in tree.getroot().findall("{%s}parent" % ns):
        parent_artifact_id = elem.find("{%s}artifactId" % ns)

    if parent_artifact_id is not None and not (
            parent_artifact_id.text == "sbforge-parent" or parent_artifact_id.text == "sbprojects-parent"):
        __move_child_pom(path, parent_artifact_id, artifact_id)


def __move_child_pom(old_pom_path, parent_artifact_id, child_artifact_id):
    parent_path_string = __create_pom_path(parent_artifact_id, old_pom_path)
    child_path_string = parent_path_string + "/" + child_artifact_id.text

    if Path(parent_path_string).exists():
        Path(child_path_string).mkdir(exist_ok=True)
        shutil.move(old_pom_path, child_path_string + "/pom.xml")
        print("Moved child pom to folder: " + child_path_string + "/pom.xml")
    else:
        print("Child move ignored: " + old_pom_path + " -> " + child_path_string + "/pom.xml")


def __create_pom_path(parent_artifact_id, pom_path):
    pom_path = pom_path.strip("/pom.xml")
    pom_path = pom_path.rsplit("/", 1)[0]
    pom_path = pom_path.split("releases/", 1)[-1]
    # artifact_id = parent_artifact_id.text.rsplit("-parent", 1)[0] + "-parent"
    full_path_string = "new_releases/" + pom_path + "/" + parent_artifact_id.text
    return full_path_string


def __find_parents():
    for root, dirs, files in os.walk('releases/'):
        if files and files[0] == "pom.xml":
            __pom_parent_finder(os.path.join(root, files[0]))


def __find_children(children_left):
    files_skipped = 0
    if children_left:
        for root, dirs, files in os.walk('releases/'):
            if files and files[0] == "pom.xml":
                __pom_child_finder(os.path.join(root, files[0]))
                if os.path.isfile(os.path.join(root, files[0])):
                    files_skipped += 1
    if files_skipped > 0:
        print("Skipped " + str(files_skipped) + " files")
        # __find_children(files_skipped)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Need arguments")
        sys.exit(1)
    if sys.argv[1] == "nexus":
        Path("releases").mkdir(exist_ok=True)
        nexus_url = "https://sbforge.org/nexus/content/repositories/releases"
        __crawl_nexus(nexus_url, 'releases')
    if sys.argv[1] == "move":
        __find_parents()
        __find_children(True)
