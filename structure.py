import csv
import json
import logging
from configparser import ConfigParser


class Structure:
    def __init__(self):
        self.ignored_parents = ['sbforge-parent', 'sbprojects-parent', 'oss-parent']
        self.obj = {}
        self.dependency_map = {}
        self.number_of_runs = 0
        self.ns = ""
        self.config = ConfigParser()
        self.config.read("config.conf")
        self.number_of_runs = int(self.config.get("worker", "find_children_runs"))
        self.ns = {'pom': self.config.get("all", "namespace_url")}

    def setup_logging(self):
        """ Initializes the logging settings. """
        logging.basicConfig(
            format='%(asctime)s %(levelname)s: %(message)s',
            level=self.config.get("all", "logging_level").upper())

    def create_package(self, package):
        """
        Created a package in the dictionary.
        :param package: The package to create.
        """
        if package not in self.obj:
            self.obj[package] = {'modules': [], 'alt-name': []}
            logging.debug(f'Created package: {package}')

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

    def write_dependency_map_json(self):
        """ Writes the dependency map to a .json file. """
        with open('dependency_map.json', 'w') as output:
            json.dump(self.dependency_map, output)
        logging.info('Dependency map written to .json file.')
