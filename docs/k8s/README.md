## Kubernetes examples

First, edit `config.yaml` and fill out the config values. Also, check `pvc.yaml` and verify the "storageClassName" is correct for your cluster.

Then apply the yaml files:

#### Kubectl +1.14.x 
```
# Creating resources
kubectl apply -f config.yaml
kubectl apply -f pvc.yaml
kubectl apply -f statefulset.yaml
```
