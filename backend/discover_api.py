"""
Discover Railway GraphQL schema to find correct deployment mutation.
"""
import requests

REFRESH_TOKEN = "4K54eP_2Fxoc_UPclnE9R4TOFJ1RiVViH2ODcT1ZgqU"
CLIENT_ID = "rlwy_oaci_onEklvmksh1hRUiCo7E2zX12"
API = "https://backboard.railway.com"

# Get token
r = requests.post(f"{API}/oauth/token", data={
    "grant_type": "refresh_token",
    "refresh_token": REFRESH_TOKEN,
    "client_id": CLIENT_ID,
})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Get schema introspection
introspection = """
{
  __schema {
    mutationType {
      fields {
        name
        description
        args {
          name
          type {
            name
            kind
          }
        }
      }
    }
  }
}
"""
r = requests.post(f"{API}/graphql/v2", json={"query": introspection}, headers=headers)
data = r.json()
mutations = data.get("data", {}).get("__schema", {}).get("mutationType", {}).get("fields", [])
print("Available mutations:")
for m in mutations:
    name = m["name"]
    args = [a["name"] for a in m.get("args", [])]
    if "deploy" in name.lower():
        print(f"  {name}({', '.join(args)})")
print()
print("All deployment-related mutations:")
for m in mutations:
    if "deploy" in name.lower():
        print(f"  {name}")

# Also check queries
queries_query = """
{
  __schema {
    queryType {
      fields {
        name
      }
    }
  }
}
"""
r = requests.post(f"{API}/graphql/v2", json={"query": queries_query}, headers=headers)
data = r.json()
queries = data.get("data", {}).get("__schema", {}).get("queryType", {}).get("fields", [])
deploy_queries = [q["name"] for q in queries if "deploy" in q["name"].lower()]
print("\nDeploy-related queries:")
print(deploy_queries)
