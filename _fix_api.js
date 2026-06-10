const https = require('https');
const T = 'tWzzzCqM6Bs1c9SORHeXAm2Ye0gueAOsRxPwSgOj1c4';
function gql(q, v) {
  return new Promise((resolve) => {
    const d = JSON.stringify({query: q, variables: v});
    const o = {hostname: 'backboard.railway.app', path: '/graphql/v2', method: 'POST', headers: {'Authorization': 'Bearer '+T, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(d)}};
    const r = https.request(o, (res) => { let b = ''; res.on('data', c => b += c); res.on('end', () => resolve(JSON.parse(b))); });
    r.write(d); r.end();
  });
}
async function main() {
  const mut = 'mutation($sid: String!, $in: ServiceInstanceUpdateInput!) { serviceInstanceUpdate(serviceId: $sid, input: $in) }';
  const r = await gql(mut, {sid: '58e77560-0286-4f5d-9778-e5d32d64f5c6', in: {rootDirectory: '', dockerfilePath: 'Dockerfile', startCommand: 'uvicorn main:app --host 0.0.0.0 --port $PORT', healthcheckPath: '/health', healthcheckTimeout: 30, restartPolicyType: 'ON_FAILURE', restartPolicyMaxRetries: 3}});
  console.log(JSON.stringify(r));
}
main();
