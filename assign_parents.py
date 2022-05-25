from lxml import etree

from utility import map_dependency_version, find_dependencies


def __find_parents(path, struct):
    """
    Traverses the tree and assign parent poms to the 'structure' dictionary.
    :param path: The given absolute path to the pom.xml file.
    :return: Returns 1 if a parent is created, 0 otherwise.
    """
    tree = etree.parse(path)
    has_parent = False
    ns = struct.ns

    for node in tree.xpath('//pom:parent/pom:artifactId', namespaces=ns):
        if node is not None and node.text not in struct.ignored_parents:
            has_parent = True
            break

    if not has_parent:
        package_id = tree.xpath('./pom:groupId', namespaces=ns)[0].text.lower()
        struct.create_package(package_id)
        parent_id = tree.xpath('./pom:artifactId', namespaces=ns)[0].text.lower()
        version = 'n/a' if len(tree.xpath('./pom:version', namespaces=ns)) == 0 else tree.xpath('./pom:version', namespaces=ns)[0].text
        # Maps the versions that are declared through properties in the parent pom to their actual values
        map_dependency_version(package_id, parent_id, version, tree)
        struct.obj[package_id]['modules'].append(
            {'name': parent_id, 'version': version, 'modules': [], 'dependencies': find_dependencies(tree, None)})

        return 1
    return 0
