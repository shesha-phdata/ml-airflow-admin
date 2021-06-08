# Admin Dag Project

Admin Dag project deploys two files `scan_dag_file.py` and `sync_ml_project_dags.py` in Admin Dag S3 directory `edx-${Enviornment}-${AWS::Region}-airflow-admin` which is created as part of `wolkaws-healthgrades -> airflow -> master-ecs.yaml` stack.

- Dag `sync_ml_project_dags.py` is responsible to ship project Dags   
  from their S3 bucket to Airflow External Project Dag Folder
- `scan_dag_file.py` is an util python class which is responsible to
  perform following validation on Dag code before it's shipped from S3
  to Dag directory.
    - For every Dag code file, dag_id name should start with the project name and **-prj-** followed after the project name.
    - Dag file should be a .py code

# Code Deployment Process

1. Create a new branch from master branch `feature/<CHANGEID>_<TITLE>`
2. Create a Merge Request and add Approver to the PR
3. Once PR is Approved by the Approver, next process is to deploy to AWS DEV/PROD S3 bucket `edx-${Enviornment}-${AWS::Region}-airflow-admin`
4. Using comment based deploy Allowed Build Deploy Owner is suppose to provide following comment to deploy to Dev **"cf deploy dev"**, this would trigger a Jenkins build.
5. Once Jenkins build is successfull, developers are expected to verify the Dag behaviour in Airflow and confirm if deployment should be done to Prod.
6. Using comment based deploy Allowed Build Deploy Owner is suppose to provide following comment to deploy to Dev **"cf deploy prod"**, this would trigger a Jenkins build.

# Jenkins and Gitlab integration
Please refer to following [document](https://healthgrades.atlassian.net/wiki/spaces/HPE/pages/1449656915/phData) to get an overview of how Gitlab and Jenkins are integrated.