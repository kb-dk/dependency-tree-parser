import csv
import json
import os
import subprocess
import sys

from lxml import etree

structure = {}
dependency_map = {}
obj = {}

url = "http://maven.apache.org/POM/4.0.0"
ns = {
    "pom": url
}

ignored_parents = ["sbforge-parent", "sbprojects-parent", "oss-parent"]
strings_to_replace = ["${parent.artifactid}", "${parent.artifactId}", "${project.parent.artifactId}", "${project.parent.artifactid}"]


def run(file_type, path='releases/'):
    global structure
    global obj
    global dependency_map
    total_nr_of_poms = __count_poms(path)
    poms_left = total_nr_of_poms

    # Assign parent poms
    for root, dirs, files in os.walk(path):
        if files and files[0] == "pom.xml":
            poms_left -= __find_parents(os.path.join(root, files[0]))

    obj = json.loads(json.dumps(structure))

    # Assign children poms, run through a few times, since we can't assure correct order
    number_of_runs = 3
    for i in range(number_of_runs):
        for root, dirs, files in os.walk(path):
            if files and files[0] == "pom.xml":
                if i + 1 == number_of_runs:
                    poms_left -= __find_children(os.path.join(root, files[0]), True)
                else:
                    __find_children(os.path.join(root, files[0]))

    if poms_left > 0:
        print("Poms not assigned: " + str(poms_left) + "/" + str(total_nr_of_poms))
    else:
        print("All poms assigned.")

    # Update dependency versions
    __update_dependency_versions()

    # Remove 'alt-name' since it is redundant information at this point
    __remove_alt_name()

    # Either output csv or json file, depending on the given output.
    if file_type == "csv":
        __write_csv()
    elif file_type == "json":
        __write_json(obj)
    else:
        print("Argument '" + file_type + "' is not a valid file-type, use csv or json.")


def __find_parents(path):
    global structure, obj
    tree = etree.parse(path)
    has_parent = False

    for node in tree.xpath("//pom:parent/pom:artifactId", namespaces=ns):
        if node is not None and node.text not in ignored_parents:
            has_parent = True
            break

    if not has_parent:
        package = tree.xpath("./pom:groupId", namespaces=ns)[0].text.lower()
        __create_package(package)
        parent_id = tree.xpath("./pom:artifactId", namespaces=ns)[0].text.lower()
        version = "n/a" if len(tree.xpath("./pom:version", namespaces=ns)) == 0 else tree.xpath("./pom:version", namespaces=ns)[0].text
        # Maps the versions that are declared through properties in the parent pom to their actual values
        __map_dependency_version(package, version, tree)
        structure[package]['modules'].append(
            {parent_id: version, 'modules': [], 'dependencies': __find_dependencies(tree, package, parent_id)})

        return 1
    return 0


def __map_dependency_version(package_id, version, tree):
    properties = tree.xpath("./pom:properties", namespaces=ns)
    old_maps = dependency_map[package_id] if package_id in dependency_map else []
    maps = []
    project_version_created = False
    for x in old_maps:
        if '${project.version}' in x:
            project_version_created = True
    if not project_version_created:
        maps.append({'${project.version}': version})

    for p in properties:
        for i in range(len(p)):
            property_text = p[i].text
            if "${" in property_text:
                property_text = __check_version(package_id, property_text)
            tag = str(p[i].tag).split('}', 1)[-1]
            maps.append({'${' + tag + '}': property_text})
    dependency_map[package_id] = old_maps + maps


def __check_version(package_id, version):
    for key, val in obj.items():
        if package_id in val['alt-name']:
            package_id = key

    if version and '${' in version and package_id in dependency_map:
        for i in dependency_map[package_id]:
            if version in i:
                return i[version]
    return version


def __update_dependency_versions():
    for key, val in obj.items():
        for parent in val['modules']:
            __update_version(key, parent)
            for child in parent['modules']:
                __update_version(key, child)
                for inner_child in child['modules']:
                    __update_version(key, inner_child)


def __update_version(package_id, module):
    for dependencies in module['dependencies']:
        for dependency, version in dependencies.items():
            new_version = __check_version(package_id, version)
            module[dependency] = new_version


def __find_children(path, last_round=False):
    created = False
    tree = etree.parse(path)
    alt_package_id, child_id, dependencies, package_id, parent_id, version = __get_pom_vars(tree)

    if parent_id is None or (parent_id in ignored_parents):
        return 0
    if package_id in obj:
        # Handle alternative names using extra groupIds defined in poms
        alt_list = obj[package_id]['alt-name']
        if alt_package_id is not None and alt_package_id not in alt_list:
            alt_list.append(alt_package_id)

        # Maps the versions that are declared through properties in the parent pom to their actual values
        __map_dependency_version(package_id, version, tree)

        # If parent exists in this layer, then insert child in modules list
        parent_modules = obj[package_id]['modules']
        modules_list = [list(dic.keys())[0] for dic in parent_modules]
        if parent_id in modules_list:
            created = __add_child(child_id, version, dependencies, parent_modules[modules_list.index(parent_id)])

        # Going deeper in the structure
        else:
            # FIXME: Make this recursive for better readability
            for mod in parent_modules:
                parent = list(mod.items())[0][0]
                index = list(mod.keys()).index(parent)
                current_modules = parent_modules[index]['modules']
                for inner_mod in current_modules:
                    parent = list(inner_mod.items())[0][0]
                    index2 = list(inner_mod.keys()).index(parent)
                    if parent_id == parent:
                        created = __add_child(child_id, version, dependencies, current_modules[index2])
                        break
                    else:
                        current_modules_2 = current_modules[index2]['modules']
                        for inner_mod_2 in current_modules_2:
                            parent = list(inner_mod_2.items())[0][0]
                            index3 = list(inner_mod_2.keys()).index(parent)
                            if parent_id == parent:
                                created = __add_child(child_id, version, dependencies, current_modules_2[index3])
                                break
                            else:
                                current_modules_3 = current_modules_2[index3]['modules']
                                for inner_mod_3 in current_modules_3:
                                    parent = list(inner_mod_3.items())[0][0]
                                    index4 = list(inner_mod_3.keys()).index(parent)
                                    if parent_id == parent:
                                        created = __add_child(child_id, version, dependencies, current_modules_3[index4])
                                        break

    # Created is None if pom was skipped due to already having being created.
    if created:
        return 1
    # If child was not created due to parent not being found, try using alternative parent name
    elif not created:
        created_using_alt_name = __find_children_alt_name(parent_id, package_id, child_id, alt_package_id, version, dependencies)
        # If created successfully return 1
        if created_using_alt_name:
            return 1
        # If it was not created, and not skipped due to being a duplicate print the path that was skipped.
        elif not created_using_alt_name and last_round:
            print(path)
            print("     | " + package_id + " (" + str(alt_package_id) + ")" + " | " + str(parent_id) + " | " + str(child_id))
        return 0


def __create_package(package):
    if package not in structure:
        structure[package] = {'modules': [], 'alt-name': []}


def __get_pom_vars(tree):
    global obj
    # Find child artifactID
    child_id = tree.xpath("./pom:artifactId", namespaces=ns)[0].text.lower()
    # Use parents version if it does not have its own version defined.
    version = tree.xpath("//pom:parent/pom:version", namespaces=ns)[0].text if len(tree.xpath("./pom:version", namespaces=ns)) == 0 else \
        tree.xpath("./pom:version", namespaces=ns)[0].text
    # GroupId of parent is used to find package in structure dictionary
    package_id = tree.xpath("//pom:parent/pom:groupId", namespaces=ns)[0].text.lower() if len(tree.xpath("//pom:parent/pom:groupId",
                                                                                                         namespaces=ns)) != 0 else None
    # Extra groupId will be used as alternative name
    alt_package_id = tree.xpath("./pom:groupId", namespaces=ns)[0].text.lower() if len(tree.xpath("./pom:groupId",
                                                                                                  namespaces=ns)) > 0 else None
    # Parent artifactID, None if there's no parent ID
    parent_id = tree.xpath("//pom:parent/pom:artifactId", namespaces=ns)[0].text.lower() if len(tree.xpath("//pom:parent/pom:artifactId",
                                                                                                           namespaces=ns)) != 0 else None
    # Maps the versions that are declared through properties in the parent pom to their actual values
    __map_dependency_version(package_id, version, tree)
    dependencies = __find_dependencies(tree, package_id, parent_id)

    return alt_package_id, child_id, dependencies, package_id, parent_id, version


# TODO: Use __fix_name to correct artifactIds
def __fix_name(name, parent_id):
    # Fix specific case where child-poms' artifactId points to its parents' artifactId.
    for string in strings_to_replace:
        if string in name:
            return name.replace(string, parent_id)
    return name


def __add_child(child_id, version, dependencies, index):
    exists = any(d.get(child_id) for d in index['modules'])
    if not exists:
        index['modules'].append({child_id: version, 'modules': [], 'dependencies': dependencies})
    return True


def __find_children_alt_name(parent_id, package_id, child_id, alt_package_id, version, dependencies):
    # FIXME: Make this recursive for better readability
    for key, val in obj.items():
        alt_name = val['alt-name']
        if alt_name is not None and package_id in alt_name:
            for module in range(len(obj[key]['modules'])):
                inner_modules = obj[key]['modules'][module]['modules']
                for inner in inner_modules:
                    if parent_id in inner:
                        alt_list = obj[key]['alt-name']
                        if alt_package_id is not None and alt_package_id not in alt_list:
                            alt_list.append(alt_package_id)
                        return __add_child(child_id, version, dependencies, inner)
                    else:
                        inner_modules_2 = inner_modules[inner_modules.index(inner)]['modules']
                        for inner_2 in inner_modules_2:
                            if parent_id in inner_2:
                                alt_list = obj[key]['alt-name']
                                if alt_package_id is not None and alt_package_id not in alt_list:
                                    alt_list.append(alt_package_id)
                                return __add_child(child_id, version, dependencies, inner_2)
                            else:
                                inner_modules_3 = inner_modules_2[inner_modules_2.index(inner_2)]['modules']
                                for inner_3 in inner_modules_3:
                                    if parent_id in inner_3:
                                        alt_list = obj[key]['alt-name']
                                        if alt_package_id is not None and alt_package_id not in alt_list:
                                            alt_list.append(alt_package_id)
                                        return __add_child(child_id, version, dependencies, inner_3)
            return False


def __find_dependencies(tree, package_id, parent_id):
    global obj
    dependencies = []
    pom_dependencies = tree.xpath("//pom:dependencies/pom:dependency", namespaces=ns)

    for dependency in pom_dependencies:
        dependency_name = dependency.xpath("./pom:artifactId", namespaces=ns)[0].text
        dependency_name = __fix_name(dependency_name, parent_id)
        dependency_version = dependency.xpath("./pom:version", namespaces=ns)
        version = dependency_version[0].text if dependency_version else "inherited"
        dependencies.append({dependency_name: __check_version(package_id, version)})

    return dependencies


def __remove_alt_name():
    for key, val in obj.items():
        obj[key].pop('alt-name')


def __write_json(string):
    with open('structure.json', 'w') as output:
        json.dump(string, output)
    print("Structure written to .json file.")


def __write_csv():
    fields = ['package', 'modules', 'dependencies', 'alt-name']
    with open('structure.csv', 'w') as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        for key, val in sorted(obj.items()):
            row = {'package': key}
            row.update(val)
            writer.writerow(row)
    print("Structure written to .csv file.")


def __count_poms(path="releases/"):
    counter = 0
    for _, _, files in os.walk(path):
        if files and files[0] == "pom.xml":
            counter += 1
    return counter


@DeprecationWarning
def __count_tgfs():
    counter = 0
    for _, _, files in os.walk('tgfs/'):
        counter = len(files)
    return counter


@DeprecationWarning
def __create_tgfs():
    current_path = os.getcwd()
    for root, dirs, files in os.walk('releases/'):
        if files and files[0] == "pom.xml":
            print("Found file at: " + os.path.join(root))
            if not os.path.exists(os.path.join(current_path, 'tgfs', root.rsplit('/', 1)[-1]) + '.tgf'):
                print("     Creating tgf: " + os.path.join(current_path, 'tgfs', root.rsplit('/', 1)[-1]) + '.tgf')
                __run_dependency_tree(root, os.path.join(current_path, 'tgfs', root.rsplit('/', 1)[-1]) + '.tgf')
            else:
                print("     Skipping, already exists.")


@DeprecationWarning
def __run_dependency_tree(pom_path, output_path):
    command = 'cd ' + pom_path + ' && mvn dependency:tree -DoutputFile=' + output_path + ' -DoutputType=tgf'
    try:
        process = subprocess.Popen(command, shell=True)
        subprocess.Popen.wait(process)
    except subprocess.CalledProcessError as e:
        print('>>>>> ERROR <<<<<')
        print(e.output)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Need file-type as argument. Specific path as 2nd argument is optional.")
        sys.exit(1)
    else:
        if len(sys.argv) > 2:
            run(sys.argv[1], sys.argv[2])
        else:
            run(sys.argv[1])
