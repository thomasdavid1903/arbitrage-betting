import os
import main

modules_not_found = []

try:
    import urllib
except ModuleNotFoundError as e:
    modules_not_found.append(str(str(e).split('\'')[1]))

try:
    import bs4
except ModuleNotFoundError as e:
    modules_not_found.append(str(str(e).split('\'')[1]))

for item in modules_not_found:
    os.system(f'pip install {item}')

if __name__ == "__main__":
    main()
