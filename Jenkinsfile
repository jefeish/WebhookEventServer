pipeline {
    agent any

    stages {
        withCredentials([usernamePassword(credentialsId: 'githubapp-jenkins',
                              usernameVariable: 'GITHUB_APP',
                              passwordVariable: 'GITHUB_ACCESS_TOKEN')]) {
            stage('Build') {
                steps {

                    echo 'Building..'

                }
            }
            stage('Test') {
                steps {
                    echo 'Testing..'
                }
            }
            stage('Deploy') {
                steps {
                    echo 'Deploying....'
                }
            }
        }  
    }
} 
