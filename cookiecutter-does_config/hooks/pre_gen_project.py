import os, sys

from os.path import relpath

#os.path.relpath(dest, start)


#print("here")
#print(f"cwd={os.getcwd()}")

relative_path = "{{ cookiecutter.relative_path_does_config_to_doespy }}"
poetry_path = os.path.join(relative_path, "pyproject.toml")
if not os.path.exists(poetry_path):
    print(f"relative_path_does_config_to_doespy not set properly, did not find: {poetry_path}")
    rel = os.path.relpath(os.path.join(os.environ.get("PWD"), "doespy"), os.getcwd())
    print(f"  relative_path_does_config_to_doespy should be set to: {rel}  (but currently is: {{ cookiecutter.relative_path_does_config_to_doespy }})")
    sys.exit(1)

#else:




#    print(f"should be = {rel}")

#import subprocess
#rel = os.path.relpath(os.path.join(os.environ.get("PWD"), "doespy"), os.getcwd())
#rel = "numpy"
#out = subprocess.check_output(f"ls", shell=True)
#print(f"lsout={out}")
#out = subprocess.check_output(f"poetry add {rel}", shell=True)

#out = subprocess.Popen(["poetry", "add", "rel"])

#print(f"old={os.environ.get('OLDPWD')}")
#print(f"cur={os.environ.get('PWD')}")
#
#
#print("context={{ cookiecutter }}")
