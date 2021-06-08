pipeline {
    environment {
     stage = 'build'
     GITLAB_SVC_ACCNT_TOKEN = credentials('svc_jenkins_airflow_api')
     BUCKET_SUFFIX = "us-east-1-airflow-admin"
     TARGET_DIR = "admin_dags"
     cloudfoundation_approved_users = credentials('cloudfoundation_approved_users')
     gitlab_api_url = "https://git.healthgrades.com"
    }
    agent {label 'edx-infra ec2 slave'}
    stages {
       stage('PRE-BUILD') {
         when {
            expression { env.gitlabMergeRequestIid != null && ( env.gitlabTriggerPhrase == 'cf deploy dev' || env.gitlabTriggerPhrase == 'cf deploy sbx' || env.gitlabTriggerPhrase == 'cf deploy prod' ) }
          }
          steps {
            updateGitlabCommitStatus name: 'build', state: 'pending'
            sh 'printenv'
            sh 'git checkout $gitlabMergeRequestLastCommit'
            sh """
            echo "Build started on `date`"
            chmod +x bin/validate_approver.sh
            """
          }
       }
       stage('PUSH to DEV'){
         when {
            expression { env.gitlabTriggerPhrase == 'cf deploy dev' &&  env.gitlabMergeRequestState != 'opened'}
          }
          environment {
             deploy_environment="dev"
             pr_status="DEPLOY"
            }
          steps {
            sh 'printenv'
            withCredentials([
              [$class: 'AmazonWebServicesCredentialsBinding', accessKeyVariable: 'AWS_ACCESS_KEY_ID', credentialsId: 'svc_airflow', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']
              ]) {
              catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                sh """
                bin/validate_approver.sh
                aws s3 cp admin_dags/ s3://edx-$deploy_environment-${BUCKET_SUFFIX}/$TARGET_DIR/ --recursive
                """
              }
            }
          }
       }
       stage('PUSH to SBX'){
         when {
            expression { env.gitlabTriggerPhrase == 'cf deploy sbx' &&  env.gitlabMergeRequestState != 'opened'}
          }
          environment {
             deploy_environment="sbx"
             pr_status="DEPLOY"
            }
          steps {
            sh 'printenv'
            withCredentials([
              [$class: 'AmazonWebServicesCredentialsBinding', accessKeyVariable: 'AWS_ACCESS_KEY_ID', credentialsId: 'svc_airflow_prod', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']
              ]) {
              catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                sh """
                bin/validate_approver.sh
                aws s3 cp admin_dags/ s3://edx-$deploy_environment-${BUCKET_SUFFIX}/$TARGET_DIR/ --recursive
                """
              }
            }
          }
       }
      stage('PUSH to PROD'){
          when {
            expression { env.gitlabTriggerPhrase == 'cf deploy prod' &&  env.gitlabMergeRequestState != 'opened'}
          }
          environment {
             deploy_environment="prod"
             pr_status="DEPLOY"
          }
          steps {
            withCredentials([
              [$class: 'AmazonWebServicesCredentialsBinding', accessKeyVariable: 'AWS_ACCESS_KEY_ID', credentialsId: 'svc_airflow_prod', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']
              ]) {
              catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                sh """
                bin/validate_approver.sh
                aws s3 cp admin_dags/ s3://edx-$deploy_environment-${BUCKET_SUFFIX}/$TARGET_DIR/ --recursive
                """
              }
            }
          }
      }
    }
    post {
        always {
            // withEnv(['stage=post_build']) {
            // // withCredentials([string(credentialsId: 'GITLAB_SVC_ACCNT_TOKEN', variable: 'GITLAB_SVC_ACCNT_TOKEN')])
            //   catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
            //       sh """
            //       cd $project
            //       $WORKSPACE/gitlab_jenkins_build.sh
            //       """
            //   }
            // }
            cleanWs()
        }
        success {
            updateGitlabCommitStatus name: 'build', state: 'success'
        }
        failure {
            updateGitlabCommitStatus name: 'build', state: 'failed'
        }
    }
}
