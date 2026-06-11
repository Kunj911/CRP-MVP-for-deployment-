"""
Deploy backend to Railway via API.
Uses stored refresh token to get a fresh access token, then triggers deployment.
"""
import json
import time
import requests

REFRESH_TOKEN = "4K54eP_2Fxoc_UPclnE9R4TOFJ1RiVViH2ODcT1ZgqU"
PROJECT_ID = "d87b7501-8247-4965-af91-a5d26c3c94b3"
SERVICE_ID = "0850b159-e772-41d2-8e40-0488b4b8e377"
ENV_ID = "25e0308a-cc3f-4a43-ac80-9dae31102fba"
CLIENT_ID = "rlwy_oaci_onEklvmksh1hRUiCo7E2zX12"

API = "https://backboard.railway.com"

def refresh_token():
    """Get a fresh access token from Railway's OAuth endpoint."""
    r = requests.post(f"{API}/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
    })
    if r.status_code != 200:
        print(f"Token refresh FAILED: {r.status_code} {r.text[:200]}")
        return None
    data = r.json()
    print(f"Token refreshed. Expires in {data.get('expires_in', '?')}s")
    return data["access_token"]

def trigger_deployment(token):
    """Trigger a Railway deployment via GraphQL API."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    mutation = """
    mutation Deploy($serviceId: String!, $environmentId: String!) {
        deploymentCreate(
            input: {
                serviceId: $serviceId
                environmentId: $environmentId
            }
        ) {
            id
            status
            url
        }
    }
    """
    r = requests.post(f"{API}/graphql/v2", json={
        "query": mutation,
        "variables": {
            "serviceId": SERVICE_ID,
            "environmentId": ENV_ID,
        }
    }, headers=headers)
    if r.status_code != 200:
        print(f"Deploy trigger FAILED: {r.status_code} {r.text[:300]}")
        return None
    data = r.json()
    if data.get("errors"):
        print(f"GraphQL error: {data['errors']}")
        return None
    deploy = data["data"]["deploymentCreate"]
    print(f"Deployment created: id={deploy['id']} status={deploy['status']}")
    return deploy["id"]

def wait_for_deploy(token, deploy_id, timeout_sec=300):
    """Poll until deployment completes."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    query = """
    query DeployStatus($id: String!) {
        deployment(id: $id) {
            id
            status
            createdAt
            updatedAt
        }
    }
    """
    start = time.time()
    while time.time() - start < timeout_sec:
        r = requests.post(f"{API}/graphql/v2", json={
            "query": query,
            "variables": {"id": deploy_id}
        }, headers=headers)
        if r.status_code == 200:
            data = r.json()
            if not data.get("errors"):
                status = data["data"]["deployment"]["status"]
                print(f"  Status: {status}")
                if status == "DEPLOYMENT_STATUS_SUCCESS":
                    print("  DEPLOYMENT SUCCESSFUL!")
                    return True
                if status in ("DEPLOYMENT_STATUS_FAILED", "DEPLOYMENT_STATUS_CRASHED"):
                    print(f"  DEPLOYMENT FAILED with status: {status}")
                    return False
        time.sleep(5)
    print(f"  TIMEOUT after {timeout_sec}s")
    return False

print("=== Railway Deployment ===")
token = refresh_token()
if not token:
    print("Cannot deploy without a valid token.")
    print("Please run: railway login")
    exit(1)

deploy_id = trigger_deployment(token)
if not deploy_id:
    print("Failed to create deployment.")
    exit(1)

print(f"Deployment ID: {deploy_id}")
print("Waiting for deployment to complete...")
success = wait_for_deploy(token, deploy_id)
if success:
    print("Backend deployed successfully!")
else:
    print("Deployment did not complete successfully.")
    exit(1)
