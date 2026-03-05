# from flask import Flask, jsonify, request
# from flask_cors import CORS
# import random
# import time

# app = Flask(__name__)

# # Enable CORS for all routes
# CORS(app)

# @app.route("/api/kernel-status1/<kernel_id>", methods=["GET"])
# def pending_kernel(kernel_id):

#     # simulate kernel scheduling randomness
#     pending = random.choice([True, False])

#     print(f"Received status request for kernel_id={kernel_id}, Pending: {pending}")

#     if pending:
#         return jsonify({
#             "pending": True,
#             "pod": "kernel-user-abc123",
#             "status": "Pending",
#             "message": "Waiting for Kubernetes scheduler"
#         })
#     else:
#         return jsonify({
#             "pending": False,
#             "status": "Running",
#             "message": "Kernel ready"
#         })


# @app.route("/health")
# def health():
#     return jsonify({"status": "ok"})


# if __name__ == "__main__":
#     print("Mock Kubernetes API server running on http://localhost:9000")
#     app.run(host="0.0.0.0", port=9000, debug=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

app = FastAPI()

# Allow JupyterLab extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Kubernetes config (works both locally and inside cluster)
try:
    config.load_incluster_config()
    print("Loaded in-cluster Kubernetes config")
except ConfigException:
    config.load_kube_config()
    print("Loaded local kubeconfig")

v1 = client.CoreV1Api()


@app.get("/api/kernel-status/{kernel_id}")
def kernel_status(kernel_id: str):

    try:
        pods = v1.list_pod_for_all_namespaces(
            label_selector=f"component=kernel,kernel_id={kernel_id}"
        )

        if not pods.items:
            return {
                "kernel_id": kernel_id,
                "status": "NotFound",
                "message": "No kernel pod found"
            }

        pod = pods.items[0]

        return {
            "kernel_id": kernel_id,
            "namespace": pod.metadata.namespace,
            "pod": pod.metadata.name,
            "status": pod.status.phase
        }

    except Exception as e:
        return {
            "kernel_id": kernel_id,
            "status": "Error",
            "message": str(e)
        }


@app.get("/health")
def health():
    return {"status": "ok"}
