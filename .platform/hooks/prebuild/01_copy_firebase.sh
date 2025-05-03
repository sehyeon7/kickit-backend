#!/usr/bin/env bash
set -euxo pipefail

# 1) /etc/secrets 준비
mkdir -p /etc/secrets
chmod 700 /etc/secrets

# 2) AWS Secrets Manager에서 JSON을 가져와 저장
aws --region ap-northeast-2 secretsmanager get-secret-value \
  --secret-id firebase/credentials \
  --query SecretString --output text \
  > /etc/secrets/firebase.json

# 3) 권한 타이트닝
chmod 600 /etc/secrets/firebase.json
chown root:root /etc/secrets/firebase.json
