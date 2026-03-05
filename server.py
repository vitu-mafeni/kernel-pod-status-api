from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import client, config, watch
from kubernetes.config.config_exception import ConfigException
import threading

app = FastAPI()

# Enable CORS for JupyterLab extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Kubernetes config
try:
    config.load_incluster_config()
    print("Loaded in-cluster config")
except ConfigException:
    config.load_kube_config()
    print("Loaded kubeconfig")

v1 = client.CoreV1Api()

# Cache of kernel statuses
kernel_cache = {}


def watch_kernel_pods():
    w = watch.Watch()

    for event in w.stream(
        v1.list_pod_for_all_namespaces,
        label_selector="component=kernel"
    ):

        pod = event["object"]

        labels = pod.metadata.labels or {}

        kernel_id = labels.get("kernel_id")

        if not kernel_id:
            continue

        kernel_cache[kernel_id] = {
            "kernel_id": kernel_id,
            "namespace": pod.metadata.namespace,
            "pod": pod.metadata.name,
            "status": pod.status.phase
        }

        print(f"Kernel {kernel_id} -> {pod.status.phase}")


@app.on_event("startup")
def start_watcher():
    thread = threading.Thread(target=watch_kernel_pods, daemon=True)
    thread.start()


@app.get("/api/kernel-status/{kernel_id}")
def kernel_status(kernel_id: str):

    if kernel_id not in kernel_cache:
        return {
            "kernel_id": kernel_id,
            "status": "NotFound"
        }

    return kernel_cache[kernel_id]


@app.get("/api/kernels")
def list_kernels():
    return kernel_cache


@app.get("/health")
def health():
    return {"status": "ok"}