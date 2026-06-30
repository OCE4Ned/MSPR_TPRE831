pipeline {
  agent any

  parameters {
    booleanParam(name: 'FORCE_BUILD_ALL', defaultValue: false,
                 description: 'Build et déploie tous les services, ignore le git diff')
  }

  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
    disableConcurrentBuilds()
  }

  environment {
    REGISTRY      = 'hub.ecluse.cloud'
    REGISTRY_CRED = 'docker-registry'
    VPS_SSH_CRED  = 'vps-ssh-key'
    VPS_HOST      = 'deploy@ecluse.cloud'
    VPS_PATH      = '/srv/mecha'
    IMAGE_TAG     = "${env.GIT_COMMIT.take(7)}"
  }

  stages {
    stage('Detect changes') {
      steps {
        script {
          if (params.FORCE_BUILD_ALL) {
            env.CHANGED_FRONTEND = 'true'
            env.CHANGED_BACKEND  = 'true'
            env.CHANGED_IA       = 'true'
            env.CHANGED_PIPELINE = 'true'
            env.CHANGED_AIRFLOW  = 'true'
            env.CHANGED_DEPLOY   = 'true'
            env.CHANGED_ETL      = 'true'
            echo "FORCE_BUILD_ALL=true — tous les services seront buildés"
          } else {
            def changed = sh(
              script: 'git diff --name-only HEAD~1 HEAD',
              returnStdout: true
            ).trim().split('\n')

            env.CHANGED_FRONTEND = changed.any { it.startsWith('frontend/') }    ? 'true' : 'false'
            env.CHANGED_BACKEND  = changed.any { it.startsWith('backend/') }     ? 'true' : 'false'
            env.CHANGED_IA       = changed.any { it.startsWith('api_ia/') }      ? 'true' : 'false'
            env.CHANGED_DEPLOY   = changed.any { it.startsWith('deployments/compose.yaml') || it == 'deployments/compose.yaml' } ? 'true' : 'false'

            // Pipeline : scripts kafka + Dockerfile.pipeline + ses requirements
            env.CHANGED_PIPELINE = changed.any {
              it ==~ /pipeline\/(kafka_.+|machine_.+)\.py/ ||
              it == 'pipeline/docker/Dockerfile.pipeline' ||
              it == 'pipeline/docker/requirements-pipeline.txt'
            } ? 'true' : 'false'

            // Airflow : DAGs + Dockerfile.airflow + ses requirements
            env.CHANGED_AIRFLOW = changed.any {
              it.startsWith('pipeline/airflow/') ||
              it == 'pipeline/docker/Dockerfile.airflow' ||
              it == 'pipeline/docker/requirements-airflow.txt'
            } ? 'true' : 'false'

            // ETL : compose ou SQL d'init → redéploie sans rebuild forcément
            env.CHANGED_ETL = changed.any {
              it == 'deployments/compose.etl.yml' ||
              it == 'deployments/init-postgres.sql'
            } ? 'true' : 'false'

            echo "frontend=${env.CHANGED_FRONTEND} backend=${env.CHANGED_BACKEND} ia=${env.CHANGED_IA} pipeline=${env.CHANGED_PIPELINE} airflow=${env.CHANGED_AIRFLOW} deploy=${env.CHANGED_DEPLOY} etl=${env.CHANGED_ETL} tag=${env.IMAGE_TAG}"
          }
        }
      }
    }

    stage('Build & push') {
      parallel {
        stage('Frontend') {
          when { expression { env.CHANGED_FRONTEND == 'true' } }
          steps { script { buildAndPush('frontend') } }
        }

        stage('Backend') {
          when { expression { env.CHANGED_BACKEND == 'true' } }
          steps { script { buildAndPush('backend') } }
        }

        stage('IA API') {
          when { expression { env.CHANGED_IA == 'true' } }
          steps { script { buildAndPush('api_ia') } }
        }

        stage('Pipeline') {
          when { expression { env.CHANGED_PIPELINE == 'true' } }
          steps { script { buildAndPushPipeline('pipeline', 'Dockerfile.pipeline') } }
        }

        stage('Airflow') {
          when { expression { env.CHANGED_AIRFLOW == 'true' } }
          steps { script { buildAndPushPipeline('airflow', 'Dockerfile.airflow') } }
        }
      }
    }

    stage('Deploy app') {
      when {
        expression {
          env.CHANGED_FRONTEND == 'true' ||
          env.CHANGED_BACKEND  == 'true' ||
          env.CHANGED_IA       == 'true' ||
          env.CHANGED_DEPLOY   == 'true'
        }
      }
      steps {
        sshagent([env.VPS_SSH_CRED]) {
          sh """
            scp -o StrictHostKeyChecking=no \\
              deployments/compose.yaml \\
              ${env.VPS_HOST}:${env.VPS_PATH}/compose.yaml

            ssh -o StrictHostKeyChecking=no ${env.VPS_HOST} '
              cd ${env.VPS_PATH} && \\
              export IMAGE_TAG=${env.IMAGE_TAG} && \\
              docker compose pull --ignore-pull-failures && \\
              docker compose up -d --remove-orphans && \\
              docker image prune -f
            '
          """
        }
      }
    }

    stage('Deploy ETL') {
      when {
        expression {
          env.CHANGED_PIPELINE == 'true' ||
          env.CHANGED_AIRFLOW  == 'true' ||
          env.CHANGED_ETL      == 'true'
        }
      }
      steps {
        sshagent([env.VPS_SSH_CRED]) {
          sh """
            scp -o StrictHostKeyChecking=no \\
              deployments/compose.etl.yml \\
              deployments/init-postgres.sql \\
              ${env.VPS_HOST}:${env.VPS_PATH}/

            ssh -o StrictHostKeyChecking=no ${env.VPS_HOST} '
              cd ${env.VPS_PATH} && \\
              export IMAGE_TAG=${env.IMAGE_TAG} && \\
              docker compose -f compose.etl.yml pull --ignore-pull-failures && \\
              docker compose -f compose.etl.yml up -d --remove-orphans && \\
              docker image prune -f
            '
          """
        }
      }
    }
  }

  post {
    success { echo "Déploiement ${env.IMAGE_TAG} réussi" }
    failure { echo "Échec du déploiement ${env.IMAGE_TAG}" }
    always  { cleanWs() }
  }
}


def buildAndPush(String service) {
  def image  = "${env.REGISTRY}/mecha/${service}:${env.IMAGE_TAG}"
  def latest = "${env.REGISTRY}/mecha/${service}:latest"

  dir(service) {
    sh "docker build -t ${image} -t ${latest} ."
  }

  pushImage(image, latest)
}


def buildAndPushPipeline(String service, String dockerfile) {
  def image  = "${env.REGISTRY}/mecha/${service}:${env.IMAGE_TAG}"
  def latest = "${env.REGISTRY}/mecha/${service}:latest"

  dir('pipeline') {
    sh "docker build -f docker/${dockerfile} -t ${image} -t ${latest} ."
  }

  pushImage(image, latest)
}


def pushImage(String image, String latest) {
  withCredentials([usernamePassword(
      credentialsId: env.REGISTRY_CRED,
      usernameVariable: 'REG_USER',
      passwordVariable: 'REG_PASS')]) {
    sh """
      echo \$REG_PASS | docker login ${env.REGISTRY} -u \$REG_USER --password-stdin
      docker push ${image}
      docker push ${latest}
      docker logout ${env.REGISTRY}
    """
  }
}