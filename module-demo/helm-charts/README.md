# dmeo 部署

## 使用示例
```bash
helm upgrade fit2cloud-demo-deployment --namespace=fit2cloud --install --force --recreate-pods  --set="modules.imagePullPolicy=Always,modules.imageTag=3.0.0,,cmp.logLevel=DEBUG" fit2cloud3/fit2cloud-demo-deployment
```