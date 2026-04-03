#!/usr/bin/env bash
set -euo pipefail

echo "$CI_REGISTRY_PASSWORD" | docker login -u "$CI_REGISTRY_USER" --password-stdin "$CI_REGISTRY"

if [ -n "${CI_COMMIT_TAG:-}" ]; then
  docker pull "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA"
  docker tag "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA" "$CI_REGISTRY_IMAGE:$CI_COMMIT_TAG"
  docker push "$CI_REGISTRY_IMAGE:$CI_COMMIT_TAG"
else
  docker build -t "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA" .
  docker push "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA"
  docker tag "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA" "$CI_REGISTRY_IMAGE:$CI_COMMIT_REF_SLUG"
  docker push "$CI_REGISTRY_IMAGE:$CI_COMMIT_REF_SLUG"
fi

printf "IMAGE_REF=%s\nIMAGE_TAG=%s\n" "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA" "$CI_COMMIT_SHA" > build.env

if [ -n "${CI_COMMIT_TAG:-}" ]; then
  printf "CLI_ARTIFACT_URL=%s/api/v4/projects/%s/packages/generic/memory-cli/%s/memory-cli-linux-amd64-%s.tar.gz\n" "$CI_SERVER_URL" "$CI_PROJECT_ID" "$CI_COMMIT_TAG" "$CI_COMMIT_TAG" >> build.env
fi
