import os
from datetime import date
from summary import load

# print(project_path)
today = date.today()


def make_save_dir(path_name, *date):

    # print(path_name)

    save_dir = project_path + '\\Analysis\\' + path_name
    if date:
        save_dir = save_dir + '\\' + today.strftime("%Y-%m-%d")
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)


if __name__ == '__main__':
    make_save_dir(path_name, date)
