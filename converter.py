import csv
import sys

packages = {}
dependencies = []
csv_output = []


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


def load_file():
    path = sys.argv[1]

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


def create_csv_data():
    for key, val in packages.items():
        package, version = split_name_and_version(val)

        for info in dependencies:
            if key == info[0]:
                dependency, dependency_version = split_name_and_version(packages[info[1]])
                csv_output.append(
                    [package, version, dependency, dependency_version, info[2]]
                )


def create_csv():
    path = sys.argv[1].strip(".tgf") + ".csv"
    fields = ["application-name", "application-version", "depends-on-lib", "lib-version", "scope"]

    with open(path, 'w', encoding='UTF8', newline='') as file:
        # To write Dict
        # writer = csv.DictWriter(file, fieldnames=fields)
        # writer.writerows(dict_data)

        # To write List
        list_writer = csv.writer(file)
        list_writer.writerow(fields)
        list_writer.writerows(csv_output)

    file.close()


load_file()
create_csv_data()
create_csv()
