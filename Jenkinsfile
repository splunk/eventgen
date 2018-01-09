@Library('jenkinstools@master') _

withSplunkWrapNode('orca_ci') {
    // Determine if the build was triggered by branch activity, user, or timer
    def causes = splunkUtils.getCauses()
    def credentialsAWS = [$class: 'AmazonWebServicesCredentialsBinding',
                          credentialsId: 'tools-jenkins-aws',
                          accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                          secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']
    currentBuild.result = 'SUCCESS'
    def minSuccessful = 5

    // Setup Stash notifications
    step([$class: 'StashNotifier'])

    echo "Build triggered by: ${causes}"

    try {
        stage('Checkout') {
            internalNotifyBuild('STARTED')
            checkout scm
        }

        stage('Run tests') {
            echo "test"
            sh 'make test'
        }

        stage('Parse results') {
            junit 'test*.xml'
        }

        stage('Publish pypi') {
            if (env.BRANCH_NAME == 'develop') {
                sh 'make push_egg_production'
            }
        }

        stage('Publish image') {
            if (env.BRANCH_NAME == 'develop') {
                sh 'make push_image_production'
            }
        }

        stage('Publish documentation') {
            CHANGED_FILES = sh returnStdout: true,
                               script: 'git --no-pager diff HEAD^ HEAD --name-only'
            echo "${CHANGED_FILES}"
            if (env.BRANCH_NAME == 'develop' && CHANGED_FILES.contains('documentation/')) {
                sh 'make docs'
            }
            else {
                echo 'Skip publishing docs...'
            }
        }

    }
    catch (Exception e) {
        echo "Exception Caught: ${e.getMessage()}"
        currentBuild.result = 'FAILURE'
        // want to collect and parse test results so we get a nice notification on hipchat
        junit 'test*.xml'
    } 
    finally {
        step([$class: 'StashNotifier'])
        internalNotifyBuild(currentBuild.result)

        stage('Clean') {
            sh 'docker system prune -f'
            deleteDir()
        }
    }
}

def internalNotifyBuild(String buildStatus = 'STARTED') {

    // build status of null means successful
    buildStatus =  buildStatus ?: 'SUCCESS'

    // Default values
    def colorName = 'RED'
    def subject = "${buildStatus}: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'"
    def summary = "${subject} (${env.BUILD_URL})"
    def details = """<p>STARTED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]':</p>
      <p>Check console output at "<a href="${env.BUILD_URL}">${env.JOB_NAME} [${env.BUILD_NUMBER}]</a>"</p>"""

    // Override default values based on build status
    if (buildStatus == 'STARTED') {
        color = 'YELLOW'
        colorCode = '#FFFF00'
    } else if (buildStatus == 'SUCCESS') {
        color = 'GREEN'
        colorCode = '#00FF00'
    } else {
        color = 'RED'
        colorCode = '#FF0000'
    }

    // Send notifications
    hipchatSend (color: color, notify: true, message: summary)
}
