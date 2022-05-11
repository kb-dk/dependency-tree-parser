import os
import subprocess
import sys

from lxml import etree

url = "http://maven.apache.org/POM/4.0.0"
ns = {
    "pom": url
}


def __traverse_releases():
    for root, dirs, files in os.walk('releases/'):
        if files and files[0] == "pom.xml":
            __remove_modules(os.path.join(root, files[0]))


def __remove_modules(path):
    tree = etree.parse(path)

    for node in tree.xpath("//pom:modules", namespaces=ns):
        if node:
            node.getparent().remove(node)
    tree.write(path)
    print("<Modules> removed from: " + path)


def __count_poms():
    counter = 0
    for _, _, files in os.walk('releases/'):
        if files and files[0] == "pom.xml":
            counter += 1
    return counter


def __count_tgfs():
    counter = 0
    for _, _, files in os.walk('tgfs/'):
        counter = len(files)
    return counter


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
        print("Need arguments")
        sys.exit(1)
    if sys.argv[1] == "clean":
        __traverse_releases()
    if sys.argv[1] == "tgf":
        __create_tgfs()
    if sys.argv[1] == "progress":
        print(str(__count_tgfs()) + " / " + str(__count_poms()))
