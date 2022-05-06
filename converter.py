import csv
import os
import sys

packages = {}
dependencies = []
csv_output = []
path = sys.argv[1]
path_name, extension = os.path.splitext(path)
csv_path = sys.argv[2]
csv_lines = []


def last(string, delimiter):
    """Return the last element from string, after the delimiter

    If string ends in the delimiter or the delimiter is absent,
    returns the original string without the delimiter.
    """
    prefix, delim, postfix = string.rpartition(delimiter)
    return postfix if (delim and postfix) else prefix


def split_name_and_version(val):
    """Returns the package name and version.

    If the last word of the value given is either "test", "compile" or "runtime" it is removed from the string.
    When this is done, or it is not the case, we know that the last "word" of the string is the version number, using ":" as a delimiter.
    """
    last_word = last(val, ":")
    if last_word == "test" or last_word == "compile" or last_word == "runtime":
        tmp_package = val[:-(len(last_word) + 1)]
        version = last(tmp_package, ":")
        package = tmp_package[:-(len(version) + 1)]
    else:
        version = last(val, ":")
        package = val[:-(len(version) + 1)]
    return package, version


def load_files():
    """ Loads the file givens as the first argument to the script.
    The data is expected to be of type .tgf, if this is not the case, the script will exit with error-code 0.

    When the file is loaded, it will be split on the delimiter "#" into two strings.
    The first part of the split contains each package's ID.
    The second part contains the information about which package uses another package, and in what scope this happens.
    """
    global csv_lines

    if extension != ".tgf":
        print("File needs to be of type .tgf")
        sys.exit(1)

    with open(path) as file:
        text = file.read()
        output = text.split("#")
        tmp = output[0].split("\n")
        for info in tmp:
            if info:
                split = info.split(" ")
                packages[split[0]] = split[1]
        tmp = output[1].split("\n")
        for info in tmp:
            if info:
                dependencies.append(info.split(" "))
    file.close()

    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding='UTF8') as csv_file:
            reader = csv.reader(csv_file, delimiter=",")
            for row in reader:
                csv_lines.append(row)
        csv_file.close()


def row_already_in_csv(line_to_check):
    """Loads the .csv file and checks if the given line is already in the .csv file."""
    if line_to_check in csv_lines:
        return True
    return False


def create_csv_data():
    """Given the dictionary with the packages, and the list of which package uses another, create the wanted output format.
    """
    for key, val in packages.items():
        package, version = split_name_and_version(val)

        for info in dependencies:
            if key == info[0]:
                dependency, dependency_version = split_name_and_version(packages[info[1]])
                row = [os.path.basename(path)[:-4], package, version, dependency, dependency_version, info[2]]
                if not row_already_in_csv(row):
                    csv_output.append(row)


def create_csv():
    """Creates the actual .csv file locally. The file will be created the same place as the input file, given as the first argument to
    the script. """
    fields = ["project-name", "package-name", "package-version", "depends-on", "version", "scope"]
    write_fields = False
    if not row_already_in_csv(fields):
        write_fields = True

    with open(csv_path, 'w', encoding='UTF8', newline='') as file:
        list_writer = csv.writer(file)
        if csv_lines:
            list_writer.writerows(csv_lines)

        if write_fields:
            list_writer.writerow(fields)
        list_writer.writerows(csv_output)
    file.close()


load_files()
create_csv_data()
create_csv()
