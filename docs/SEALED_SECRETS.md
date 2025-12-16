# Sealed Secrets Implementation Guide

## Overview

Sealed Secrets allow you to encrypt Kubernetes Secrets and store them safely in Git. The sealed secrets can only be decrypted by the controller running in the cluster.

## Installation (Cluster Admin Required)

### 1. Install Sealed Secrets Controller
```bash
# Install the controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Verify installation
kubectl get pods -n kube-system | grep sealed-secrets
```

### 2. Install kubeseal CLI
```bash
# Linux
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz
tar -xvzf kubeseal-0.24.0-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal

# Verify
kubeseal --version
```

## Usage

### Create a Sealed Secret from Existing Secret
```bash
# Export existing secret
kubectl get secret db-credentials -n tom-wakhungu -o yaml > db-credentials-secret.yaml

# Create sealed secret
kubeseal -f db-credentials-secret.yaml -w db-credentials-sealed.yaml \
  --controller-namespace kube-system \
  --controller-name sealed-secrets-controller

# The sealed secret can now be committed to Git!
git add k8s/db-credentials-sealed.yaml
git commit -m "Add sealed database credentials"
git push
```

### Create New Sealed Secret from Scratch
```bash
# Create regular secret YAML (don't commit this!)
kubectl create secret generic db-credentials \
  --from-literal=host=innovation.c3m2emiiu9qh.eu-west-1.rds.amazonaws.com \
  --from-literal=database=tom_wakhungu_medicine_inventory \
  --from-literal=username=admin \
  --from-literal=password='YOUR_PASSWORD' \
  --namespace=tom-wakhungu \
  --dry-run=client -o yaml > temp-secret.yaml

# Seal it
kubeseal -f temp-secret.yaml -w k8s/db-credentials-sealed.yaml

# Delete temp file (contains plain text password!)
rm temp-secret.yaml

# Commit sealed secret (encrypted - safe to store in Git)
git add k8s/db-credentials-sealed.yaml
```

### Apply Sealed Secret
```bash
# Apply the sealed secret to cluster
kubectl apply -f k8s/db-credentials-sealed.yaml

# The controller will automatically decrypt it and create the regular secret
kubectl get secret db-credentials -n tom-wakhungu
```

## SealedSecret Example
```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: db-credentials
  namespace: tom-wakhungu
spec:
  encryptedData:
    host: AgBhY2R... (encrypted)
    database: AgCxZ3J... (encrypted)
    username: AgDkN2F... (encrypted)
    password: AgEyM3Q... (encrypted)
    port: AgFpN3U... (encrypted)
  template:
    metadata:
      name: db-credentials
      namespace: tom-wakhungu
    type: Opaque
```

## Benefits

✅ **Safe to store in Git** - Encrypted secrets can be version controlled  
✅ **No manual secret management** - GitOps friendly  
✅ **Cluster-specific** - Can only be decrypted in the target cluster  
✅ **Audit trail** - All changes tracked in Git history

## Security Notes

- Never commit unsealed secrets to Git
- Sealed secrets are cluster-specific (can't be used in different clusters)
- Rotation requires creating new sealed secrets
- Keep kubeseal version in sync with controller version

## Alternative: External Secrets Operator

For production environments, consider using External Secrets Operator with AWS Secrets Manager:
```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

This allows integration with AWS Secrets Manager, HashiCorp Vault, etc.

