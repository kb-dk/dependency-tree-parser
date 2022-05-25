import logging

from lxml import etree

from utility import get_pom_vars


def __find_children(path, util, last_round=False):
    """
    Runs through the poms and assigns children to their respective parents in the dictionary.

    Also assigns alternative names, by looking at poms that have double group IDs.
    Ensures to map dependencies if new <properties> definitions are found.
    :param path: The relative path of the pom.xml file.
    :param last_round: Used to indicate that it is the last run through of assigning poms.
    :return: Returns 1 of the pom was assigned in the dictionary, 0 otherwise.
    """
    obj = util.obj
    created = False
    tree = etree.parse(path)
    alt_package_id, child_id, dependencies, package_id, parent_id, version = get_pom_vars(tree)

    # Skip pom if it has no <parent> or the <parent> tag contains specific strings.
    if parent_id is None or (parent_id in util.ignored_parents):
        return 0
    if package_id in obj:
        # Handle alternative names using extra groupIds defined in poms.
        alt_list = obj[package_id]['alt-name']
        if alt_package_id is not None and alt_package_id not in alt_list:
            alt_list.append(alt_package_id)

        # If parent exists in this layer, then insert child in modules list
        created = __recursive_add_children(parent_id, obj[package_id]['modules'], child_id, version, dependencies)

    # Created is None if pom was skipped due to already having being created.
    if created:
        return 1
    # If child was not created due to parent not being found, try using alternative parent name
    elif not created:
        created_using_alt_name = __find_children_alt_name(util, parent_id, package_id, child_id, alt_package_id, version, dependencies)
        # If created successfully return 1
        if created_using_alt_name:
            return 1
        # If it was not created, and not skipped due to being a duplicate print the path that was skipped.
        elif not created_using_alt_name and last_round:
            logging.debug(f'Could not assign: {path}')
            logging.debug(f'         -| {package_id} ({str(alt_package_id)})  :  {str(parent_id)}  :  {str(child_id)}')
    return 0


def __find_children_alt_name(util, parent_id, package_id, child_id, alt_package_id, version, dependencies):
    """
    Assigns child pom information to the dictionary, where the package ID (group ID) is defined using an alternative name.
    :param parent_id: The parent artifact ID found in the <parent> tag.
    :param package_id: The package group ID of the <parent> tag.
    :param child_id: The artifact ID of the pom itself.
    :param alt_package_id: The alternative package ID, found if the pom has two group IDs.
    :param version: The version found in the pom.
    :param dependencies: The dependencies of the pom.
    :return: True of the child was assigned in the dictionary, False otherwise.
    """
    for key, val in util.obj.items():
        alt_names = val['alt-name']
        if alt_names is not None and package_id in alt_names:
            if alt_package_id is not None and alt_package_id not in alt_names:
                logging.debug(f'Alt-name \'{alt_package_id}\' added to \'{key}\'.')
                alt_names.append(alt_package_id)
            return __recursive_add_children(parent_id, util.obj[key]['modules'], child_id, version, dependencies)
    return False


def __recursive_add_children(parent_id, current_modules, child_id, version, dependencies):
    """
    Recursively tries to add the child pom to a level of 'modules' in the dictionary structure.
    :param parent_id: The parent ID from the child pom.
    :param current_modules: The current 'modules' list.
    :param child_id: The child ID from the pom (artifact ID of the pom)
    :param version: The version of the module, as described in the pom.
    :param dependencies: The dependencies found under the <dependencies> tag in the pom.
    :return: Return True if the child pom was created in the dictionary, False otherwise.
    """
    for inner_mod in current_modules:
        if parent_id == inner_mod['name']:
            created = __add_child(child_id, version, dependencies, inner_mod)
        else:
            created = __recursive_add_children(parent_id, inner_mod['modules'], child_id, version, dependencies)
        if created:
            return True
    return False


def __add_child(child_id, version, dependencies, module):
    """
    Assigns the given child pom information to the dictionary if it does not already exist.
    :param child_id: The child pom artifact ID.
    :param version: The module ID.
    :param dependencies: The dependencies found in the pom.
    :param module: The index in the dictionary.
    :return: Returns True
    """
    if child_id not in [x['name'] for x in module['modules']]:
        logging.debug(f'Created: {child_id}.')
        module['modules'].append({'name': child_id, 'version': version, 'modules': [], 'dependencies': dependencies})
    else:
        logging.debug(f'Skipped: {child_id} - already exists.')
    return True
