import sys
import os
from importlib import import_module,util
import logging
from airflow import DAG

log = logging.getLogger(__name__)

def main():
    projdir = sys.argv[1]
    sys.path.append(projdir)

    print(f"Validating modules for project {projdir}...")

    def test_dag_module(module,fullpath):
        print(f"Module Name: {module}")
        print(f"Module Full Path: {fullpath}")

        try:
            testmod = import_module(module)
        except ModuleNotFoundError as e:
            spec = util.spec_from_file_location(module, fullpath)
            testmod = util.module_from_spec(spec)

        for name in dir(testmod):
            thing = getattr(testmod, name)
            if type(thing) is DAG:
                if (( not thing.dag_id.startswith(projdir)) or (thing.dag_id.count("-prj-") <= 0)):
                    print(f"FAIL: Bad DAG ID: {module}: {thing.dag_id}."
                          " DAG IDs must start with the project and '-prj-' followed after the project name"
                          f"name: {projdir}")
                    sys.exit(1)
                print(f"Found valid DAG name: {thing.dag_id}")

    for currpath,dirs,files in os.walk(projdir):
        for filename in files:
            if not filename.endswith('.py'):
                continue
            fullpath = os.path.join(currpath, filename)
            script = open(fullpath).read()
            if 'airflow' in script and 'DAG' in script:
                test_dag_module(filename[:-3],fullpath)

    print(f"Validation complete for {projdir}.")

if __name__ == '__main__':
    main()
