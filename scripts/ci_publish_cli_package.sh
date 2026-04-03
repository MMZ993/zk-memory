#!/usr/bin/env bash
set -euo pipefail

cd cli
mkdir -p dist
go build -o dist/memory .
tar -C dist -czf "dist/memory-cli-linux-amd64-${CI_COMMIT_TAG}.tar.gz" memory
curl --fail --header "JOB-TOKEN: $CI_JOB_TOKEN" --upload-file "dist/memory-cli-linux-amd64-${CI_COMMIT_TAG}.tar.gz" "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/generic/memory-cli/${CI_COMMIT_TAG}/memory-cli-linux-amd64-${CI_COMMIT_TAG}.tar.gz"
