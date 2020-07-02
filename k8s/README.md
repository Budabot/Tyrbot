## Kubernetes examples

### Directory structure

|Directory|Description|
|---------|-----------|
|k8s/example/base/*|Base manifestos|
|k8s/example/overlay/<environment>/|Customization for the environment|
|k8s/example/overlay/<environment>/secrets|Configuration and secrets|    

#### Kubectl +1.14.x 
```
# Creating resources
cd example/overlay/example
kubectl apply -f .
```

### Kustomize setup
```
# Creating resources
cd example/overlay/example
kustomize build . |kubectl -f -
```

