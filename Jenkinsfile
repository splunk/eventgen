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
            sh 'make test'
        }

        stage('Parse results') {
            junit 'test*.xml'
        }

        stage('Publish pypi') {
            sh 'make push_egg_staging'
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

// TODO - move internal methods to jenkinstools library
def internalCountLastSuccessful(build, maxCount) {
    passedBuilds = 0
    for (i = 0; i < maxCount; i++) {
        build = build.getPreviousBuild()
        if (build == null) {
            break
        }
        else if (build.result == 'SUCCESS') {
            passedBuilds += 1
        }
    }
    return passedBuilds
}
