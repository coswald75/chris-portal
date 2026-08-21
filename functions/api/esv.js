// Cloudflare Pages Function — ESV passage proxy.
// Holds the Crossway key as a Pages secret (env.ESV_API_KEY); the client never
// sees it. GET /api/esv?ref=<reference>  ->  { ref, html }.
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const ref = (url.searchParams.get("ref") || "").slice(0, 120).trim();
  const json = (obj, status = 200) =>
    new Response(JSON.stringify(obj), {
      status,
      headers: { "content-type": "application/json", "cache-control": "public, max-age=86400" },
    });
  if (!ref) return json({ error: "missing ref" }, 400);
  if (!env.ESV_API_KEY) return json({ error: "ESV key not configured" }, 503);

  const api = new URL("https://api.esv.org/v3/passage/html/");
  api.searchParams.set("q", ref);
  api.searchParams.set("include-passage-references", "true");
  api.searchParams.set("include-footnotes", "false");
  api.searchParams.set("include-headings", "false");
  api.searchParams.set("include-audio-link", "false");
  api.searchParams.set("include-short-copyright", "false");
  api.searchParams.set("include-passage-horizontal-lines", "false");
  api.searchParams.set("include-heading-horizontal-lines", "false");

  let r;
  try {
    r = await fetch(api.toString(), { headers: { Authorization: "Token " + env.ESV_API_KEY } });
  } catch (e) {
    return json({ error: "fetch failed" }, 502);
  }
  if (!r.ok) return json({ error: "esv " + r.status }, 502);
  const data = await r.json();
  const html = (data.passages || []).join("").trim();
  if (!html) return json({ error: "not found", ref }, 404);
  return json({ ref: data.canonical || ref, html });
}
