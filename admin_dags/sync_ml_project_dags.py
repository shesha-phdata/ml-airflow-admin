import os
from datetime import datetime,timedelta
import subprocess
import tempfile
import shutil

import airflow
from airflow.models import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

import boto3

args = {
    'owner': 'Airflow',
    'start_date': datetime(2019, 11, 12)
}

def get_account_alias():
    iam = boto3.client('iam')
    aliases = iam.list_account_aliases().get('AccountAliases', [])
    if aliases:
        return aliases[0]
    return "NO_ALIAS"

def get_region_name():
    session = boto3.session.Session()
    return session.region_name

def build_bucket_basename(env):
    alias = get_account_alias()
    region = get_region_name()
    return f"{env}-{alias}-{region}-mlp-"

def list_buckets(**kwargs):
    ret = []
    client = boto3.client('s3')
    environment = os.environ['ENVIRONMENT']
    bucket_start = build_bucket_basename(environment)

    buckets = client.list_buckets()
    bucket_list = buckets['Buckets']
    for b in bucket_list:
        name = b['Name']
        if not name.startswith(bucket_start):
            continue
        ret.append(name)
    return ret

def sync_project_dags(**kwargs):
    environment = os.environ['ENVIRONMENT']
    bucket_start = build_bucket_basename(environment)

    task_instance = kwargs['task_instance']
    bucket_list = task_instance.xcom_pull(task_ids='list_buckets')
    temp_directory = task_instance.xcom_pull(key="temp_directory")
    os.chdir(temp_directory)

    has_failures = False
    for b in bucket_list:
        s3 = boto3.client('s3')

        timestamps = []
        try:
            query = {
                "Bucket": b,
                "Prefix": "code/dags/",
                "Delimiter": "/",
            }
            while True:
                r = s3.list_objects_v2(**query)
                prefixes = r.get('CommonPrefixes', [])
                timestamps.extend([prefix['Prefix'].split('/')[2] for prefix in prefixes])
                try:
                    query['ContinuationToken'] = r['NextContinuationToken']
                except KeyError:
                    break
        except Exception as e:
            print(f"Listing bucket {b} failed: {str(e)}")

        if not len(timestamps):
            continue

        timestamps.sort()
        latest = timestamps[-1]
        print(f"Selected latest timestamp: {latest}")

        projname = b[len(bucket_start):]
        print(f"SYNC START: {projname}")
        os.mkdir(projname)
        cmd = f"aws s3 sync --exact-timestamps --delete --no-progress s3://{b}/code/dags/{latest}/ ./{projname}"
        print(f"Running s3->local sync for {projname}: {cmd}")
        subprocess.run(cmd, shell=True)

        cmd = ("/usr/local/bin/python "
               f"/var/lib/airflow/dags/admin/scan_dag_file.py {projname}")
        print(f"Running check command: {cmd}")
        try:
            subprocess.run(cmd, env={'AIRFLOW_HOME': f"{temp_directory}/afhome"},
                            shell=True, capture_output=True, check=True)
        except subprocess.CalledProcessError as cpe:
            print(f"ERROR: Refusing to sync project {projname} due to DAG "
                   "validation errors.")
            print(f"STDOUT: {cpe.stdout}")
            print(f"STDERR: {cpe.stderr}")
            has_failures = True
            continue

        destpath = f"/var/lib/airflow/projectdags/{projname}"
        cmd = f"rsync -av --exclude __pycache__ --delete {projname}/ {destpath}/"
        print(f"Running local->dagroot sync for {projname}: {cmd}")
        subprocess.run(cmd, shell=True)

        print(f"Purging __pycache__ for {projname}")
        for curpath, dirs, files in os.walk(destpath):
            if '__pycache__' in dirs:
                cachedir = os.path.join(curpath, '__pycache__')
                print(f"{cachedir}")
                shutil.rmtree(cachedir)
        print(f"SYNC END: {projname}")

    if has_failures:
        raise Exception("Failing the task due to previous errors.")

def purge_obsolete_projects(**kwargs):
    environment = os.environ['ENVIRONMENT']
    bucket_start = build_bucket_basename(environment)

    task_instance = kwargs['task_instance']
    bucket_list = task_instance.xcom_pull(task_ids='list_buckets')

    active_projects = set([b[len(bucket_start):] for b in bucket_list])
    live_projects = set(os.listdir('/var/lib/airflow/projectdags'))

    obsolete_projects = live_projects - active_projects
    print(f"Purging {len(obsolete_projects)} obsolete project DAG directories...")

    for proj in obsolete_projects:
        print(f"Purging {proj}")
        projdir = os.path.join('/var/lib/airflow/projectdags', proj)
        shutil.rmtree(projdir)
    print("Done.")

def setup(**kwargs):
    task_instance = kwargs['task_instance']
    temp_directory = tempfile.mkdtemp()
    print(f"setup: Created temp directory '{temp_directory}")
    task_instance.xcom_push(key="temp_directory", value=temp_directory)

def teardown(**kwargs):
    task_instance = kwargs['task_instance']
    temp_directory = task_instance.xcom_pull(key="temp_directory")

    print(f"teardown: removing temp directory '{temp_directory}")
    shutil.rmtree(temp_directory, ignore_errors=True)
    print(f"teardown: Done removing temp directory '{temp_directory}''")

dag = DAG(
    dag_id='admin-sync_ml_project_dags',
    default_args=args,
    schedule_interval='*/30 * * * *',
    catchup=False,
    dagrun_timeout=timedelta(minutes=60),
)

setup = PythonOperator(
    task_id='setup',
    python_callable=setup,
    provide_context=True,
    dag=dag
)

teardown = PythonOperator(
    task_id='teardown',
    python_callable=teardown,
    provide_context=True,
    dag=dag
)

get_bucket_list = PythonOperator(
    task_id='list_buckets',
    python_callable=list_buckets,
    provide_context=True,
    dag=dag
)

do_sync = PythonOperator(
    task_id='sync_project_dags',
    python_callable=sync_project_dags,
    provide_context=True,
    dag=dag
)

do_purge = PythonOperator(
    task_id='purge_obsolete_projects',
    python_callable=purge_obsolete_projects,
    provide_context=True,
    dag=dag
)

setup >> get_bucket_list >> do_sync >> do_purge >> teardown

if __name__ == "__main__":
    dag.cli()
