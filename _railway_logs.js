const https = require('https');

const TOKEN = 'tWzzzCqM6Bs1c9SORHeXAm2Ye0gueAOsRxPwSgOj1c4';

function graphql(query, variables = {}) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ query, variables });
    const options = {
      hostname: 'backboard.railway.app',
      path: '/graphql/v2',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${TOKEN}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)
      }
    };
    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(body)); }
        catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function main() {
  // Get deployment with diagnosis
  const deploymentQuery = `
    query($deploymentId: String!) {
      deployment(id: $deploymentId) {
        id
        status
        staticUrl
        url
        diagnosis
        meta
        service {
          id
          name
        }
        instances {
          id
          status
        }
      }
    }
  `;

  const result = await graphql(deploymentQuery, { deploymentId: 'fce0f5a9-83e7-4608-9fb6-23087e10ba4f' });
  console.log(JSON.stringify(result, null, 2));
}

main().catch(console.error);
