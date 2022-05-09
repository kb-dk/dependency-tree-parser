import csv
import os
import sys

csv_lines = []

path, csv_path, tgf_extension, csv_extension = "", "", "", ""


def __init_paths(path_to_tgf, path_to_csv):
    """Initialize the path to the .tgf and the .csv file."""
    global path, csv_path, tgf_extension, csv_extension
    path = path_to_tgf
    csv_path = path_to_csv
    _, tgf_extension = os.path.splitext(path)
    _, csv_extension = os.path.splitext(csv_path)


def __get_prefix(string, delimiter):
    """Returns the last element after the delimiter from the given string.

    If the string ends in the delimiter or if the delimiter is absent,
    then return the original string without the delimiter.
    """
    prefix, mid, postfix = string.rpartition(delimiter)
    return postfix if (mid and postfix) else prefix


def __enforce_version(version):
    """Enforces a specific syntax for the version of a dependency.
    The rule is that every version should have a suffix, middle, and a prefix separated by periods.
    E.g. '1.0' will be '1.0.0' and '2.30' will be '2.30.0'.
    """
    splits = version.split(".")
    if len(splits) < 3:
        split = splits[-1]
        if not any(c.isalpha() for c in split):
            version = version + ".0"
            version = __enforce_version(version)
    return version


def __split_name_and_version(val):
    """Returns the package name and version.

    If the last word of the value given is either "test", "compile" or "runtime" it is removed from the string.
    When this is done, or it is not the case, we know that the last "word" of the string is the version number, using ":" as a delimiter.
    """
    last_word = __get_prefix(val, ":")
    if last_word == "test" or last_word == "compile" or last_word == "runtime":
        tmp_package = val[:-(len(last_word) + 1)]
        version = __get_prefix(tmp_package, ":")
        package = tmp_package[:-(len(version) + 1)]
    else:
        version = __get_prefix(val, ":")
        package = val[:-(len(version) + 1)]

    # The enforce_version method will change the style of every version to be prefix.middle.suffix, e.g. 1.3.0, 2.3.1, etc.
    # This method can be used if it for some reason is a problem to encode the versions as strings.
    return package, version  # __enforce_version(version)


def __row_already_in_csv(line_to_check):
    """Loads the .csv file and checks if the given line is already in the .csv file."""
    for line in csv_lines:
        if line_to_check == line:
            return True
    return False


def __load_files():
    """ Loads the file givens as the first argument to the script.
    The data is expected to be of type .tgf, if this is not the case, the script will exit with error-code 0.

    When the file is loaded, it will be split on the delimiter "#" into two strings.
    The first part of the split contains each package's ID.
    The second part contains the information about which package uses another package, and in what scope this happens.
    """
    global csv_lines
    packages = {}
    dependencies = []

    if tgf_extension != ".tgf":
        print("File needs to be of type .tgf")
        sys.exit(1)

    if csv_extension != ".csv":
        print("File needs to be of type .csv")
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
        with open(csv_path, "r", encoding="UTF8") as csv_file:
            reader = csv.reader(csv_file, delimiter=",")
            for row in reader:
                csv_lines.append(row)
        csv_file.close()

    return packages, dependencies


def __create_csv_data():
    """Given the dictionary with the packages, and the list of which package uses another, create the wanted output format.
    """
    packages, dependencies = __load_files()
    csv_data = []
    for key, val in packages.items():
        package, version = __split_name_and_version(val)

        for info in dependencies:
            if key == info[0]:
                dependency, dependency_version = __split_name_and_version(packages[info[1]])
                row = [os.path.basename(path)[:-4], package, version, dependency, dependency_version, info[2]]
                if not __row_already_in_csv(row):
                    csv_data.append(row)
    return csv_data


def create_csv(path_to_tgf, path_to_csv):
    """Using the .tgf file at the given path, create a .csv file at the other given path."""
    __init_paths(path_to_tgf, path_to_csv)
    csv_data = __create_csv_data()

    fields = ["project-name", "package-name", "package-version", "depends-on", "version", "scope"]
    write_fields = False
    if not __row_already_in_csv(fields):
        write_fields = True

    with open(csv_path, "w", encoding="UTF8", newline="") as file:
        list_writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        if csv_lines:
            list_writer.writerows(csv_lines)

        if write_fields:
            list_writer.writerow(fields)
        list_writer.writerows(csv_data)
    file.close()


create_csv(sys.argv[1], sys.argv[2])
