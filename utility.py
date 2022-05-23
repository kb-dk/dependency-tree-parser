import csv
import json
import logging
import os
from configparser import ConfigParser


class Utility:

    def __init__(self):
        self.ignored_parents = ['sbforge-parent', 'sbprojects-parent', 'oss-parent']
        self.strings_to_replace = ['${parent.artifactid}', '${parent.artifactId}', '${project.parent.artifactId}',
                                   '${project.parent.artifactid}']
        self.structure = {}
        self.obj = {}
        self.dependency_map = {}
        self.number_of_runs = 0
        self.ns = ""
        self.config = ConfigParser()
        self.config.read("config.conf")
        self.number_of_runs = int(self.config.get("worker", "find_children_runs"))
        self.ns = {'pom': self.config.get("all", "namespace_url")}

    def setup_logging(self):
        logging.basicConfig(
            format='%(asctime)s %(levelname)s: %(message)s',
            level=self.config.get("all", "logging_level").upper())

    def map_dependency_version(self, package_id, version, tree):
        """
        Maps dependencies that are defined using a name defined in <properties> tag, e.g. ${project.version}.
        :param package_id: Package ID, e.g. 'org.biterepository' or 'dk.kb.netarchivesuite'
        :param version: The version of the dependency
        :param tree: The lxml etree.parse(path) tree object.
        """
        ns = self.ns
        properties = tree.xpath('./pom:properties', namespaces=ns)
        old_maps = self.dependency_map[package_id] if package_id in self.dependency_map else []
        maps = []
        # FIXME: Case where version is ${project.version} needs to be handled differently, since every package_id can have multiple of these
        # project_version_created = False
        # for x in old_maps:
        #     if '${project.version}' in x:
        #         project_version_created = True
        # if not project_version_created:
        #     maps.append({'${project.version}': version})

        for p in properties:
            for i in range(len(p)):
                property_text = p[i].text
                if '${' in property_text:
                    property_text = self.__check_version(package_id, property_text)
                tag = str(p[i].tag).split('}', 1)[-1]
                maps.append({'${' + tag + '}': property_text})
        self.dependency_map[package_id] = old_maps + maps

    def update_dependency_versions(self):
        """
        Updates the version of every dependency found, when traversing the dictionary object.
        """
        for key, val in self.obj.items():
            for parent in val['modules']:
                self.update_version(key, parent)
                for child in parent['modules']:
                    self.update_version(key, child)
                    for inner_child in child['modules']:
                        self.update_version(key, inner_child)

    def update_version(self, package_id, parent):
        """
        Runs through each dependency in the 'dependencies' key of the dictionary.
        While running through these dependencies, their version is being updated.
        :param package_id: The package ID.
        :param parent: The modules that are currently being traversed.
        """
        for dependencies in parent['dependencies']:
            for dependency, version in dependencies.items():
                new_version = self.__check_version(package_id, version)
                dependencies[dependency] = new_version

    def __check_version(self, package_id, version):
        """
        Checks if the version of the given dependency is correct.
        :param package_id: The package ID.
        :param version: The current version.
        :return: Returns either a more readable version found in the dependency_map, or the original version.
        """
        # If the package_id is an alternative name, we need to find the "correct" package_id.
        for key, val in self.obj.items():
            if package_id in val['alt-name']:
                package_id = key

        # If the version contains the chars '${', then we try to map it to a correct version
        if version and '${' in version and package_id in self.dependency_map:
            for i in self.dependency_map[package_id]:
                if version in i:
                    logging.debug(f'Updated version: {version} -> {i[version]}')
                    return i[version]
        return version

    def create_package(self, package):
        """
        Created a package in the dictionary.
        :param package: The package to create.
        """
        if package not in self.structure:
            self.structure[package] = {'modules': [], 'alt-name': []}
            logging.debug(f'Created package: {package}')

    def get_pom_vars(self, tree):
        """
        Given the tree object, read the tags and extract the information.
        :param tree: A lxml etree.parse(path) object.
        :return: Alternative package ID, child ID, dependencies, package ID, parent ID, version
        """
        ns = self.ns
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
        self.map_dependency_version(package_id, version, tree)
        dependencies = self.find_dependencies(tree, package_id, parent_id)

        return alt_package_id, child_id, dependencies, package_id, parent_id, version

    # TODO: Use __fix_name to correct artifactIds (consider changing structure to use keys 'name' and 'version'
    def fix_name(self, name, parent_id):
        """
        Used to fix the names of dependencies or artifact IDs of poms.
        :param name: The name to fix.
        :param parent_id: The parent ID that the name belongs to.
        :return: Returns either the name of a name where the incorrect string has been replaced.
        """
        for string in self.strings_to_replace:
            if string in name:
                new_name = name.replace(string, parent_id)
                logging.debug(f'Name changed: {name} -> {new_name}')
                return new_name
        return name

    def find_dependencies(self, tree, package_id, parent_id):
        """
        Find the dependencies of the pom
        :param tree: The lxml etree.parse(path) tree object.
        :param package_id: The package ID (Group ID) in the pom.
        :param parent_id: The parent ID (Artifact ID) of the <parent> tag in the pom.
        :return: A list of dependencies.
        """
        ns = self.ns
        dependencies = []
        pom_dependencies = tree.xpath('//pom:dependencies/pom:dependency', namespaces=ns)

        for dependency in pom_dependencies:
            dependency_name = dependency.xpath('./pom:artifactId', namespaces=ns)[0].text
            dependency_name = self.fix_name(dependency_name, parent_id)
            dependency_version = dependency.xpath('./pom:version', namespaces=ns)
            version = dependency_version[0].text if dependency_version else 'inherited'
            dependencies.append({dependency_name: self.__check_version(package_id, version)})

        return dependencies

    def remove_alt_name(self):
        """ Removes the 'alt-name' key from the dictionary."""
        for key, val in self.obj.items():
            self.obj[key].pop('alt-name')
            logging.debug(f'Removed \'alt-name\' key from dictionary.')

    def write_json(self):
        """ Writes the dictionary to a .json file. """
        with open('structure.json', 'w') as output:
            json.dump(self.obj, output)
        logging.info('Structure written to .json file.')

    def write_csv(self):
        """ Writes the dictionary to a .csv file. """
        fields = ['package', 'modules', 'dependencies', 'alt-name']
        with open('structure.csv', 'w') as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            for key, val in sorted(self.obj.items()):
                row = {'package': key}
                row.update(val)
                writer.writerow(row)
        logging.info('Structure written to .csv file.')

    @staticmethod
    def count_poms(path='releases/'):
        """
        Walks through the given path and count the number of pom.xml files found.
        :param path: The path to find poms in.
        """
        counter = 0
        for _, _, files in os.walk(path):
            if files and files[0] == 'pom.xml':
                counter += 1
        return counter
