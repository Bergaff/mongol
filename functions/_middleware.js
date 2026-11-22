// The course remains public; /admin is protected at the Pages edge.
const encoder = new TextEncoder();
const cookieName = '__Host-mongol_admin';
const hours = 8 * 60 * 60;
const responseHeaders = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'};
async function sign(secret, data) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(secret), {name:'HMAC', hash:'SHA-256'}, false, ['sign']);
  const bytes = new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(data)));
  return Array.from(bytes, b => b.toString(16).padStart(2,'0')).join('');
}
function equal(a,b) { if(a.length !== b.length) return false; let diff=0; for(let i=0;i<a.length;i++) diff |= a.charCodeAt(i)^b.charCodeAt(i); return diff===0; }
function page(message='') {
  return `<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Вход в админку</title><style>body{background:#f3f1e9;color:#263d33;font:16px Arial;margin:0}main{max-width:440px;margin:12vh auto;padding:32px}h1{font:40px Georgia}label{display:block;margin:25px 0 10px}input{box-sizing:border-box;width:100%;padding:14px;border:1px solid #aebbae;background:#f8f7f0;font-size:16px}button{margin-top:20px;background:#294538;color:#f4f2e8;border:0;padding:15px 22px;cursor:pointer}p{line-height:1.6;color:#667369}</style><main><p>МОНГОЛ ХЭЛ / АДМИНКА</p><h1>Вход</h1><p>${message}</p><form method="post" action="/admin"><label for="password">Пароль администратора</label><input id="password" name="password" type="password" autocomplete="current-password" required autofocus><button>Войти</button></form></main></html>`;
}
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (!/^\/admin\/*$/.test(url.pathname)) return context.next();
  const password = context.env.ADMIN_PASSWORD;
  if (!password || password.length < 16) return new Response('Админка отключена. Задайте секрет ADMIN_PASSWORD длиной не менее 16 символов в Cloudflare Pages.', {status:503, headers:responseHeaders});
  const req=context.request;
  if (req.method === 'POST') {
    if (req.headers.get('Origin') !== url.origin) return new Response('Forbidden',{status:403,headers:responseHeaders});
    const form=await req.formData();
    if(form.get('action')==='logout') return new Response(null,{status:303,headers:{...responseHeaders,Location:'/admin','Set-Cookie':`${cookieName}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict`}});
    const candidate=String(form.get('password')||'');
    if(candidate.length>1024 || !equal(await sign(password,candidate),await sign(password,password))) return new Response(page('Неверный пароль.'),{status:401,headers:{...responseHeaders,'Content-Type':'text/html; charset=utf-8'}});
    const payload = `${Math.floor(Date.now()/1000)+hours}.${crypto.randomUUID()}`;
    const sig=await sign(password,payload);
    return new Response(null,{status:303,headers:{...responseHeaders,Location:'/admin','Set-Cookie':`${cookieName}=${payload}.${sig}; Path=/; Max-Age=${hours}; HttpOnly; Secure; SameSite=Strict`}});
  }
  if(req.method!=='GET'&&req.method!=='HEAD') return new Response('Method not allowed',{status:405,headers:responseHeaders});
  const raw=(req.headers.get('Cookie')||'').split(';').map(x=>x.trim()).find(x=>x.startsWith(cookieName+'='))?.slice(cookieName.length+1)||'';
  const parts=raw.split('.');
  if(parts.length===3 && /^\d+$/.test(parts[0]) && Number(parts[0])>Date.now()/1000 && Number(parts[0])<=Date.now()/1000+hours && equal(parts[2],await sign(password,`${parts[0]}.${parts[1]}`))) {
    const result=await context.next(); const headers=new Headers(result.headers); headers.set('Cache-Control','no-store'); return new Response(result.body,{status:result.status,headers});
  }
  return new Response(page('Доступ к рабочему пространству.'),{status:401,headers:{...responseHeaders,'Content-Type':'text/html; charset=utf-8'}});
}
