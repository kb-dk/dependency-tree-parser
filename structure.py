import csv
import json
import logging


class Structure:
    def __init__(self, number_of_runs, ns):
        self.ignored_parents = ['sbforge-parent', 'sbprojects-parent', 'oss-parent']
        self.obj = {}
        self.dependency_map = {}
        self.number_of_runs = number_of_runs
        self.ns = ns

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
        fields = ['package', 'module', 'version', 'dependency', 'dependency_version']
        with open('structure.csv', 'w', encoding="utf-8-sig") as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            self.__write_rows(writer)
        logging.info('Structure written to .csv file.')

    def __write_rows(self, writer):
        """ Sorts and writes the row to the .csv file using the csv-writer. """
        for key, val in sorted(self.obj.items()):
            rows = self.__recursively_create_rows(key, val['modules'])
            writer.writerows(sorted(rows, key=lambda i: i['module']))

    def __recursively_create_rows(self, package, obj, parent=None, parent_version=None):
        """ Recursively calls __get_row_to_append for each module in the dictionary, to reach all modules and create a row for each of
        them and their dependencies. """
        row = []
        for module in obj:
            row.extend(self.__get_row_to_append(module, package, parent, parent_version))
            row.extend(self.__recursively_create_rows(package, module['modules'], module['name'], module['version']))
        return row

    @staticmethod
    def __get_row_to_append(module, package, parent, parent_version):
        """ Creates a list of rows to be written for each dependency that a module has.
            Also ensures to add a row for each child that a parent has. """
        rows = []
        if parent and parent_version:
            rows.append({'package': package, 'module': parent, 'version': parent_version, 'dependency': module['name'],
                         'dependency_version': module['version']})
        for key, val in module['dependencies'].items():
            rows.append({'package': package, 'module': module['name'], 'version': module['version'], 'dependency': key,
                         'dependency_version': val})
        # FIXME: If it is necessary to see a module if it has no dependencies then this part can be introduced again.
        # if not module['dependencies']:
        #    rows.append({'package': package, 'module': module['name'], 'version': module['version'], 'dependency': "",
        #    'dependency_version': ""})
        return rows

    def write_dependency_map_json(self):
        """ Writes the dependency map to a .json file. """
        with open('dependency_map.json', 'w') as output:
            json.dump(self.dependency_map, output)
        logging.info('Dependency map written to .json file.')
