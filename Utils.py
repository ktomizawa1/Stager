import os

def get_files(path_to_walk):
    ret = []
    for (dirpath, dirnames, filenames) in os.walk(path_to_walk):
        path = dirpath.removeprefix(path_to_walk).removeprefix("\\")
        for filename in filenames:
            ret.append(os.path.join(path,filename))

    return ret