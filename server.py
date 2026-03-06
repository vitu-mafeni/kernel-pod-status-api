from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import client, config, watch
from kubernetes.config.config_exception import ConfigException
import threading
import requests

app = FastAPI()

# -----------------------------
# Configuration
# -----------------------------

# Enterprise Gateway URL
EG_URL = "http://192.168.3.234:32556"

# Cache of kernel pod statuses
kernel_cache = {}

# -----------------------------
# Enable CORS (needed for JupyterLab extension)
# -----------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Load Kubernetes config
# -----------------------------

try:
    config.load_incluster_config()
    print("Loaded in-cluster config")
except ConfigException:
    config.load_kube_config()
    print("Loaded kubeconfig")

v1 = client.CoreV1Api()

# -----------------------------
# Kubernetes Pod Watcher
# -----------------------------

def watch_kernel_pods():

    w = watch.Watch()

    print("Starting Kubernetes pod watcher...")

    for event in w.stream(
        v1.list_pod_for_all_namespaces,
        label_selector="component=kernel",
        timeout_seconds=0
    ):

        pod = event["object"]

        labels = pod.metadata.labels or {}

        kernel_id = labels.get("kernel_id")

        if not kernel_id:
            continue

        status = pod.status.phase

        kernel_cache[kernel_id] = {
            "kernel_id": kernel_id,
            "namespace": pod.metadata.namespace,
            "pod": pod.metadata.name,
            "status": status
        }

        print(f"[Watcher] Kernel {kernel_id} -> {status}")

# -----------------------------
# Start watcher thread
# -----------------------------

@app.on_event("startup")
def start_watcher():

    thread = threading.Thread(
        target=watch_kernel_pods,
        daemon=True
    )

    thread.start()

    print("Kernel watcher started")


# -----------------------------
# Map Jupyter Kernel -> K8s Kernel
# -----------------------------

def get_k8s_kernel_id(jupyter_kernel_id: str):

    try:

        r = requests.get(f"{EG_URL}/api/kernels")

        if r.status_code != 200:
            return None

        kernels = r.json()

        for k in kernels:

            if k["id"] == jupyter_kernel_id:

                env = k.get("env", {})

                return env.get("KERNEL_ID")

    except Exception as e:
        print("Enterprise Gateway lookup failed:", e)

    return None


# -----------------------------
# API: Kernel Status
# -----------------------------

@app.get("/api/kernel-status/{kernel_id}")
def kernel_status(kernel_id: str):

    # Translate Jupyter kernel -> Kubernetes kernel
    k8s_kernel_id = get_k8s_kernel_id(kernel_id)

    if not k8s_kernel_id:

        return {
            "kernel_id": kernel_id,
            "status": "NotFound"
        }

    if k8s_kernel_id not in kernel_cache:

        return {
            "kernel_id": kernel_id,
            "status": "Pending"
        }

    return kernel_cache[k8s_kernel_id]


# -----------------------------
# API: List cached kernels
# -----------------------------

@app.get("/api/kernels")
def list_kernels():

    return kernel_cache


# -----------------------------
# API: Health check
# -----------------------------

@app.get("/health")
def health():

    return {"status": "ok"}