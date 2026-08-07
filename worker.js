// Optional. Only needed because Cfx serves the server list with CORS open but not
// single/<code>, which holds the resource list and the players. This adds the one header
// a browser needs and nothing else.
//
// Deploy free at https://workers.cloudflare.com — paste this in, save, then set
// PROXY in index.html to your worker URL, e.g. "https://fivem-proxy.you.workers.dev".

const API = "https://frontend.cfx-services.net/api/servers";

export default {
  async fetch(req) {
    const code = new URL(req.url).pathname.split("/").filter(Boolean).pop() || "";
    if (!/^[a-z0-9]{4,12}$/i.test(code)) {
      return new Response("bad join code", { status: 400 });
    }
    const r = await fetch(`${API}/single/${code}`, { cf: { cacheTtl: 30 } });
    return new Response(r.body, {
      status: r.status,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "access-control-allow-origin": "*",
        "cache-control": "public, max-age=30",
      },
    });
  },
};
