import json
import logging
import os
import sys

from assign_children import __find_children
from assign_parents import __find_parents
from utility import Utility

util = Utility()
structure, obj, number_of_runs = util.structure, util.obj, util.number_of_runs,


def run(file_type, path='releases/'):
    """
    Main method for running the dictionary creation.

    Runs through all the poms and converting every parent pom to a dictionary structure.
    Runs through the pom again a number of times equal to a variable defined in the configs file. In these runs, it will assign
    children poms to their respective parents. The reason this needs to run > 1 times, is that we cannot guarantee that a pom which
    would be a child of the outer parent is created before we look at the pom that is the grandchild.

    :param file_type: Defines the output file-type
    :param path: Defines the path of the poms, by default uses the value 'releases/'.
    """
    total_nr_of_poms = util.count_poms(path)
    poms_left = total_nr_of_poms

    # Assign parent poms
    for root, dirs, files in os.walk(path):
        if files and files[0] == 'pom.xml':
            poms_left -= __find_parents(os.path.join(root, files[0]), util)
    util.obj = json.loads(json.dumps(structure))

    # Assign children poms, run through a few times, since we can't assure correct order
    for i in range(number_of_runs):
        for root, dirs, files in os.walk(path):
            if files and files[0] == 'pom.xml':
                if i + 1 == number_of_runs:
                    poms_left -= __find_children(os.path.join(root, files[0]), util, True)
                else:
                    __find_children(os.path.join(root, files[0]), util)

    if poms_left > 0:
        logging.info(f'Could not assign {str(poms_left)} out of {str(total_nr_of_poms)} poms.')
    else:
        logging.info('All poms assigned.')

    # Go through the dependencies to map the versions correctly to their <properties> assignments
    util.fix_dependency_versions()

    # Remove 'alt-name' since it is redundant information at this point
    util.remove_alt_name()

    # Either output csv or json file, depending on the given output.
    if file_type == 'csv':
        util.write_csv()
    elif file_type == 'json':
        write_dependency_map_json(util.dependency_map)
        util.write_json()
    else:
        print('Argument \'' + file_type + '\' is not a valid file-type, use csv or json.')


def write_dependency_map_json(dependency_map):
    """ Writes the dependency map to a .json file. """
    with open('dependency_map.json', 'w') as output:
        json.dump(dependency_map, output)
    logging.info('Dependency map written to .json file.')


if __name__ == '__main__':
    util.setup_logging()
    if len(sys.argv) < 2:
        print('Need file-type as argument. Specific path as 2nd argument is optional.')
        sys.exit(1)
    else:
        if len(sys.argv) > 2:
            run(sys.argv[1], sys.argv[2])
        else:
            run(sys.argv[1])
