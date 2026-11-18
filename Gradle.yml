meta:
  description: |-
    Additionally publishes the already-built Gradle artifacts (jar, pom, ...) to the
    Dogen Artifactory right after the normal CIB upload (publish_dev / publish_release).
    Opt-in: set dogen_upload_dev / dogen_upload_release and dogen_artifactory_project.
    A Dogen failure only marks the build UNSTABLE; the pipeline continues.
    Gradle projects only. List this template BEFORE languages/gradle-app in .cib-ci.yml.
  owner: cib-pipeline
  tags:
    - tool

env:
  dogen_upload_dev:
    value: false
    description: Also publish to Dogen on dev (snapshot) builds
  dogen_upload_release:
    value: false
    description: Also publish to Dogen on release builds
  dogen_artifactory_host:
    value: 'https://artifactory-dogen.group.echonet'
    description: Dogen Artifactory base URL (without /artifactory)
  dogen_artifactory_project:
    value: ''
    description: Dogen project prefix of the repos, e.g. p-6771
  dogen_artifactory_repo_dev:
    value: '{{env.dogen_artifactory_project}}-maven-SNAPSHOT'
    description: Dogen repo for dev (snapshot) jars
  dogen_artifactory_repo_release:
    value: '{{env.dogen_artifactory_project}}-maven-RELEASE'
    description: Dogen repo for release jars
  dogen_artifactory_credential_id:
    value: ''
    description: Jenkins credential ID of the Dogen deploy account (username/password or token)
  dogen_gradle_init_script_file:
    value: '.dogen-publish-init.gradle'
    description: Init script that adds the Dogen repo (written at publish time, holds no secrets)
  dogen_gradle_init_script_content:
    value: |
      allprojects {
        afterEvaluate {
          if (plugins.hasPlugin('maven-publish')) {
            publishing {
              repositories {
                maven {
                  name = 'dogen'
                  url = uri(System.getenv('DOGEN_ARTIFACTORY_URL'))
                  credentials {
                    username = System.getenv('DOGEN_ARTIFACTORY_USER')
                    password = System.getenv('DOGEN_ARTIFACTORY_PASSWORD')
                  }
                }
              }
            }
          }
        }
      }
    description: Gradle init script; URL and credentials come from environment variables

secrets:
  dogen_artifactory:
    jenkins:
      name: '{{env.dogen_artifactory_credential_id}}'
      # TODO: mirror the exact "type" used in tools/artifactory.yml:15-19
      type: basic

jobs:
  artifact_upload_dev:
    steps:
      - name: publish_dev
      - name: publish_dogen_dev
        if:
          and:
            - '{{env.dogen_upload_dev}}'
            - '{{env.dogen_artifactory_project}}'
  artifact_upload_release:
    steps:
      - name: publish_release
      - name: publish_dogen_release
        if:
          and:
            - '{{env.dogen_upload_release}}'
            - '{{env.dogen_artifactory_project}}'

# Separate steps => separate stages. skip_error: unstable => failure never stops the pipeline.
# Only the Dogen repository task is run, so nothing is re-published to CIB and nothing is rebuilt.
publish_dogen_dev:
  on_error:
    skip_error: unstable
  commands:
    - write:
        file: '{{env.dogen_gradle_init_script_file}}'
        text: '{{env.dogen_gradle_init_script_content}}'
    - cmd: DOGEN_ARTIFACTORY_URL={{env.dogen_artifactory_host}}/artifactory/{{env.dogen_artifactory_repo_dev}} DOGEN_ARTIFACTORY_USER={{secrets.dogen_artifactory.user}} DOGEN_ARTIFACTORY_PASSWORD={{secrets.dogen_artifactory.secret}} ./gradlew {{env.gradle_opts}} -I {{env.dogen_gradle_init_script_file}} publishAllPublicationsToDogenRepository -x check

publish_dogen_release:
  on_error:
    skip_error: unstable
  commands:
    - write:
        file: '{{env.dogen_gradle_init_script_file}}'
        text: '{{env.dogen_gradle_init_script_content}}'
    - cmd: DOGEN_ARTIFACTORY_URL={{env.dogen_artifactory_host}}/artifactory/{{env.dogen_artifactory_repo_release}} DOGEN_ARTIFACTORY_USER={{secrets.dogen_artifactory.user}} DOGEN_ARTIFACTORY_PASSWORD={{secrets.dogen_artifactory.secret}} ./gradlew {{env.gradle_opts}} -I {{env.dogen_gradle_init_script_file}} publishAllPublicationsToDogenRepository -x check
