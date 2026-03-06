python -m uvicorn mock_server:app --host 0.0.0.0 --port 9000 --reload


docker build -t vitu1/jupyter-scipy-extension:v6 .
docker push vitu1/jupyter-scipy-extension:v6


in cluster
http://enterprise-gateway.enterprise-gateway.svc.cluster.local:8888