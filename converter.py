import sys


def load_file():
    path = sys.argv[1]
    packages = {}
    dependencies = []

    with open(path) as file:
        text = file.read()
        output = text.split("#")
        tmp = output[0].split("\n")
        for info in tmp:
            if info:
                split = info.split(" ")
                packages[split[0]] = split[1]
        print(packages)
        tmp = output[1].split("\n")
        for info in tmp:
            if info:
                dependencies.append(info.split(" "))
    file.close()


load_file()
