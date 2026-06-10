const https = require('https');
const TOKEN = 'tWzzzCqM6Bs1c9SORHeXAm2Ye0gueAOsRxPwSgOj1c4';

function graphql(query, variables = {}) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ query, variables });
    const opts = { hostname: 'backboard.railway.app', path: '/graphql/v2', method: 'POST', headers: { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } };
    const req = https.request(opts, (res) => { let b = ''; res.on('data', c => b += c); res.on('end', () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); });
    req.on('error', reject); req.write(data); req.end();
  });
}

async function main() {
  const mut = `mutation($sid: String!, $in: ServiceInstanceUpdateInput!) { serviceInstanceUpdate(serviceId: $sid, input: $in) }`;
  
  // Set rootDirectory to backend, keep RAILPACK so it auto-detects Dockerfile in backend/
  const backend = await graphql(mut, {
    sid: "58e77560-0286-4f5d-9778-e5d32d64f5c6",
    in: { 
      rootDirectory: "backend",
      builder: "RAILPACK",
      dockerfilePath: null,
      startCommand: "uvicorn main:app --host 0.0.0.0 --port $PORT", 
      healthcheckPath: "/health", 
      healthcheckTimeout: 30, 
      restartPolicyType: "ON_FAILURE", 
      restartPolicyMaxRetries: 3
    }
  });
  console.log('Backend:', JSON.stringify(backend, null, 2));
}
main().catch(console.error);
