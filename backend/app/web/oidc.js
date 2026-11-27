"use strict";
let oidcConfig, oidcTokens = null, oidcRefreshing = null;
const oidcRandom = () => crypto.randomUUID() + crypto.randomUUID();
const oidcB64 = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
async function oidcSettings() {
  if (!oidcConfig) { const r = await fetch("/test-config"); if (!r.ok) throw Error("Ошибка настроек входа"); oidcConfig = await r.json(); }
  return oidcConfig;
}
async function oidcLogin() {
  const c = await oidcSettings(), verifier = oidcRandom(), state = oidcRandom();
  const challenge = oidcB64(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const redirect = location.origin + "/test";
  sessionStorage.setItem("delul_oidc_pending", JSON.stringify({verifier, state, redirect}));
  const q = new URLSearchParams({client_id:c.client_id,redirect_uri:redirect,response_type:"code",scope:"openid profile email",state,code_challenge:challenge,code_challenge_method:"S256"});
  location.assign(c.issuer + "/protocol/openid-connect/auth?" + q);
}
async function oidcExchange(data) {
  const c = await oidcSettings();
  const r = await fetch(c.issuer + "/protocol/openid-connect/token", {method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams({client_id:c.client_id,...data})});
  if (!r.ok) { oidcTokens = null; sessionStorage.removeItem("delul_oidc_tokens"); throw Error("Войдите через Keycloak заново"); }
  const t = await r.json(); oidcTokens = {...t,expires_at:Date.now()+t.expires_in*1000};
  sessionStorage.setItem("delul_oidc_tokens", JSON.stringify(oidcTokens));
}
async function oidcReady() {
  await oidcSettings();
  const q = new URLSearchParams(location.search);
  if (q.has("code") || q.has("error")) {
    const pending = JSON.parse(sessionStorage.getItem("delul_oidc_pending") || "null");
    sessionStorage.removeItem("delul_oidc_pending"); history.replaceState(null,"", "/test");
    if (!pending || pending.state !== q.get("state") || q.has("error")) throw Error("Вход отменён или устарел. Повторите вход.");
    await oidcExchange({grant_type:"authorization_code",code:q.get("code"),code_verifier:pending.verifier,redirect_uri:pending.redirect});
  } else oidcTokens = JSON.parse(sessionStorage.getItem("delul_oidc_tokens") || "null");
  if (!oidcTokens) throw Error("Войдите через Keycloak");
}
async function oidcHeaders() {
  if (!oidcTokens) throw Error("Войдите через Keycloak");
  if (Date.now() > oidcTokens.expires_at - 30000) {
    if (!oidcRefreshing) oidcRefreshing = oidcExchange({grant_type:"refresh_token",refresh_token:oidcTokens.refresh_token}).finally(() => {oidcRefreshing=null;});
    await oidcRefreshing;
  }
  return {Authorization:"Bearer " + oidcTokens.access_token};
}
async function oidcLogout() {
  const c = await oidcSettings(), hint = oidcTokens?.id_token;
  oidcTokens=null; sessionStorage.removeItem("delul_oidc_tokens"); sessionStorage.removeItem("delul_attempt");
  const q = new URLSearchParams({client_id:c.client_id,post_logout_redirect_uri:location.origin+"/test"});
  if (hint) q.set("id_token_hint",hint);
  location.assign(c.issuer+"/protocol/openid-connect/logout?"+q);
}
