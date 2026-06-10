const https = require('https');
const TOKEN = 'tWzzzCqM6Bs1c9SORHeXAm2Ye0gueAOsRxPwSgOj1c4';
function gql(q, v) {
  return new Promise((r,j) => {
    const d = JSON.stringify({query:q,variables:v});
    const o = {hostname:'backboard.railway.app',path:'/graphql/v2',method:'POST',headers:{'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json','Content-Length':Buffer.byteLength(d)}};
    const qq = https.request(o, res => { let b=''; res.on('data',c=>b+=c); res.on('end',()=>{try{r(JSON.parse(b))}catch(e){j(e)}}); });
    qq.on('error',j); qq.write(d); qq.end();
  });
}

const BACKEND_SERVICE = '58e77560-0286-4f5d-9778-e5d32d64f5c6';

async function main() {
  // Check deployment
  const depQuery = `query($sid: String!) {
    deployments(serviceId: $sid, last: 1) {
      id status meta
    }
  }`;
  const deps = await gql(depQuery, { sid: BACKEND_SERVICE });
  console.log('Full response:', JSON.stringify(deps, null, 2));
}
main().catch(console.error);
