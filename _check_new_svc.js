const https = require('https');
const QUERY_TOKEN = 'Ff78e7Ld4hZV3HPGFmWskOXW1qIB8xLnW5oTKaHoyhj';
function gql(q, v, token) {
  return new Promise((r,j) => {
    const d = JSON.stringify({query:q,variables:v});
    const o = {hostname:'backboard.railway.app',path:'/graphql/v2',method:'POST',headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json','Content-Length':Buffer.byteLength(d)}};
    const qq = https.request(o, res => { let b=''; res.on('data',c=>b+=c); res.on('end',()=>{try{r(JSON.parse(b))}catch(e){j(e)}}); });
    qq.on('error',j); qq.write(d); qq.end();
  });
}

const BACKEND_SERVICE = '0850b159-e772-41d2-8e40-0488b4b8e377';

async function main() {
  const svcQuery = `query($sid: String!) {
    service(id: $sid) {
      id name
      serviceInstances {
        edges {
          node {
            id
            builder
            rootDirectory
            dockerfilePath
            healthcheckPath
            startCommand
          }
        }
      }
    }
  }`;
  const svc = await gql(svcQuery, { sid: BACKEND_SERVICE }, QUERY_TOKEN);
  console.log('Current service config:');
  console.log(JSON.stringify(svc, null, 2));
}
main().catch(console.error);
