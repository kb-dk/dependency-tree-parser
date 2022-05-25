import logging
import os
import sys

from assign_children import __find_children
from assign_parents import __find_parents
from structure import Structure
from utility import fix_dependency_versions

struct = Structure()
obj, number_of_runs = struct.obj, struct.number_of_runs,


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
    total_nr_of_poms = count_poms(path)
    poms_left = total_nr_of_poms

    # Assign parent poms
    for root, dirs, files in os.walk(path):
        if files and files[0] == 'pom.xml':
            poms_left -= __find_parents(os.path.join(root, files[0]), struct)

    # Assign children poms, run through a few times, since we can't assure correct order
    for i in range(number_of_runs):
        for root, dirs, files in os.walk(path):
            if files and files[0] == 'pom.xml':
                if i + 1 == number_of_runs:
                    poms_left -= __find_children(os.path.join(root, files[0]), struct, True)
                else:
                    __find_children(os.path.join(root, files[0]), struct)

    if poms_left > 0:
        logging.info(f'Could not assign {str(poms_left)} out of {str(total_nr_of_poms)} poms.')
    else:
        logging.info('All poms assigned.')

    # Go through the dependencies to map the versions correctly to their <properties> assignments
    fix_dependency_versions()

    # Remove 'alt-name' since it is redundant information at this point
    struct.remove_alt_name()

    # Either output csv or json file, depending on the given output.
    if file_type == 'csv':
        struct.write_csv()
    elif file_type == 'json':
        struct.write_dependency_map_json()
        struct.write_json()
    else:
        print('Argument \'' + file_type + '\' is not a valid file-type, use csv or json.')


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


if __name__ == '__main__':
    struct.setup_logging()
    if len(sys.argv) < 2:
        print('Need file-type as argument. Specific path as 2nd argument is optional.')
        sys.exit(1)
    else:
        if len(sys.argv) > 2:
            run(sys.argv[1], sys.argv[2])
        else:
            run(sys.argv[1])
