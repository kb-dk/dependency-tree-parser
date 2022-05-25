import logging

from structure import Structure

strings_to_replace = ['${parent.artifactid}', '${parent.artifactId}', '${project.parent.artifactId}', '${project.parent.artifactid}']

structure = Structure()
dependency_map, ns, obj = structure.dependency_map, structure.ns, structure.obj


def get_pom_vars(tree):
    """
    Given the tree object, read the tags and extract the information.
    :param tree: A lxml etree.parse(path) object.
    :return: Alternative package ID, child ID, dependencies, package ID, parent ID, version
    """
    # Find child artifactID
    child_id = tree.xpath('./pom:artifactId', namespaces=ns)[0].text.lower()
    # Use parents version if it does not have its own version defined.
    version = tree.xpath('//pom:parent/pom:version', namespaces=ns)[0].text if len(tree.xpath('./pom:version', namespaces=ns)) == 0 else \
        tree.xpath('./pom:version', namespaces=ns)[0].text
    # GroupId of parent is used to find package in structure dictionary
    package_id = tree.xpath('//pom:parent/pom:groupId', namespaces=ns)[0].text.lower() if len(tree.xpath('//pom:parent/pom:groupId',
                                                                                                         namespaces=ns)) != 0 else None
    # Extra groupId will be used as alternative name
    alt_package_id = tree.xpath('./pom:groupId', namespaces=ns)[0].text.lower() if len(tree.xpath('./pom:groupId',
                                                                                                  namespaces=ns)) > 0 else None
    # Parent artifactID, None if there's no parent ID
    parent_id = tree.xpath('//pom:parent/pom:artifactId', namespaces=ns)[0].text.lower() if len(
        tree.xpath('//pom:parent/pom:artifactId',
                   namespaces=ns)) != 0 else None
    # Maps the versions that are declared through properties in the parent pom to their actual values
    map_dependency_version(alt_package_id if package_id is None else package_id, child_id, version, tree)
    dependencies = find_dependencies(tree, parent_id)

    return alt_package_id, child_id, dependencies, package_id, parent_id, version


def map_dependency_version(package_id, module_id, version, tree):
    """
    Maps dependencies that are defined using a name defined in <properties> tag, e.g. ${project.version}.
    :param package_id: Package ID, e.g. 'org.biterepository' or 'dk.kb.netarchivesuite'.
    :param module_id: The artifact ID found in the <parent> tag in the pom.
    :param version: The version of the dependency.
    :param tree: The lxml etree.parse(path) tree object.
    """
    properties = tree.xpath('./pom:properties', namespaces=ns)
    for key, val in obj.items():
        if package_id in val['alt-name']:
            package_id = key
            break

    old_maps = dependency_map[package_id] if package_id in dependency_map else {}

    maps = {module_id: {}}

    # Adds a dependency map for 'project.version' -> version found in pom.
    maps[module_id]['${project.version}'] = version

    for p in properties:
        for i in range(len(p)):
            property_text = p[i].text
            if '${' in property_text:
                pass
                # FIXME: pull info from parent?
            tag = str(p[i].tag).split('}', 1)[-1]
            maps[module_id]['${' + tag + '}'] = property_text
    maps.update(old_maps)
    dependency_map[package_id] = maps


def find_dependencies(tree, parent_id):
    """
    Find the dependencies of the pom
    :param tree: The lxml etree.parse(path) tree object.
    :param parent_id: The parent ID (Artifact ID) of the <parent> tag in the pom.
    :return: A list of dependencies.
    """
    dependencies = {}
    pom_dependencies = tree.xpath('//pom:dependencies/pom:dependency', namespaces=ns)

    for dependency in pom_dependencies:
        dependency_name = dependency.xpath('./pom:artifactId', namespaces=ns)[0].text
        dependency_name = __fix_name(dependency_name, parent_id)
        dependency_version = dependency.xpath('./pom:version', namespaces=ns)
        version = dependency_version[0].text if dependency_version else 'inherited'
        dependencies[dependency_name] = version
    return dependencies


def fix_dependency_versions():
    """
    Checks if the version of the given dependency is correct.
    :return: Returns either a more readable version found in the dependency_map, or the original version.
    """
    for key, val in obj.items():
        package_id = key
        for parent in obj[key]['modules']:
            parent_id = parent['name']
            __insert_new_version(parent, package_id, parent_id)
            __recursive_fix_dependencies(package_id, parent_id, parent['modules'], parent_id)


def __recursive_fix_dependencies(package_id, absolute_parent_id, current, closest_parent_id):
    """
    Recursively runs through the dependencies of every module to try to fix their version ID by mapping them to the dependency map.
    :param package_id: The package ID under which the modules are present in both the dependency map and the overall structure.
    :param absolute_parent_id: The ID of the parent to every single module.
    :param current: The current placement in the dictionary tree.
    """
    for module in current:
        __insert_new_version(module, package_id, absolute_parent_id)
        module['name'] = __fix_name(module['name'], closest_parent_id)
        __recursive_fix_dependencies(package_id, absolute_parent_id, module['modules'], module['name'])


def __insert_new_version(module, package_id, parent_id):
    """
    Performs the actual insertion of the name into the structure dictionary object.
    """
    for dependency in module['dependencies']:
        name, version = dependency, module['dependencies'][dependency]
        new_version = __get_new_version(module, package_id, parent_id, version)
        module['dependencies'][name] = new_version
        logging.debug(f'Updated version: {name}:{version} -> {new_version}')


def __get_new_version(module, package_id, parent_id, version):
    """
    If the version contains the chars '${', then we try to map it to a correct version, running recursively
    :return: New version
    """
    if version and '${' in version:
        new_version = dependency_map[package_id][module['name']][version] \
            if version in dependency_map[package_id][module['name']] else dependency_map[package_id][parent_id][version] \
            if version in dependency_map[package_id][parent_id] else version

        if '${' in new_version:
            new_version = __get_new_version(module, package_id, parent_id, new_version)
        return new_version
    return version


def __fix_name(name, parent_id):
    """
    Used to fix the names of dependencies or artifact IDs of poms.
    :param name: The name to fix.
    :param parent_id: The parent ID that the name belongs to.
    :return: Returns either the name of a name where the incorrect string has been replaced.
    """
    for string in strings_to_replace:
        if string in name and parent_id is not None:
            new_name = name.replace(string, parent_id)
            logging.debug(f'Name changed: {name} -> {new_name}')
            return new_name
    return name
