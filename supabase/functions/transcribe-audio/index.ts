import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// Optional hosted experiment. Disabled in the React demo unless explicitly configured.
const allowedOrigins = (Deno.env.get('ALLOWED_ORIGINS') || '').split(',').map(x => x.trim()).filter(Boolean);
const maxBase64Length = 2_800_000; // About 2 MiB decoded, not unlimited audio.
serve(async (req) => {
  const origin = req.headers.get('origin');
  if (!origin || !allowedOrigins.includes(origin)) return new Response('Forbidden origin', {status: 403});
  const headers = {'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Headers': 'authorization, apikey, content-type', 'Vary': 'Origin', 'Content-Type': 'application/json'};
  if (req.method === 'OPTIONS') return new Response(null, {headers});
  if (req.method !== 'POST') return new Response(JSON.stringify({error: 'POST required'}), {status: 405, headers});
  try {
    const bearer = req.headers.get('Authorization') || '';
    if (!bearer.startsWith('Bearer ')) return new Response(JSON.stringify({error: 'Authentication required'}), {status: 401, headers});
    const supabase = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_ANON_KEY')!);
    const {data, error} = await supabase.auth.getUser(bearer.slice(7));
    if (error || !data.user) return new Response(JSON.stringify({error: 'Authentication required'}), {status: 401, headers});
    // Stream and bound the body before parsing. Content-Length alone is untrusted.
    if (!req.body) throw new Error('Missing body');
    const reader = req.body.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maxBase64Length + 1024) {
        await reader.cancel();
        return new Response(JSON.stringify({error: 'Audio too large'}), {status: 413, headers});
      }
      chunks.push(value);
    }
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.length; }
    const {audio} = JSON.parse(new TextDecoder().decode(body));
    if (typeof audio !== 'string' || !audio || audio.length > maxBase64Length) throw new Error('Invalid audio');
    const bytes = Uint8Array.from(atob(audio), c => c.charCodeAt(0));
    const key = Deno.env.get('OPENAI_API_KEY');
    if (!key) throw new Error('Transcription is not configured');
    const form = new FormData();
    form.append('file', new Blob([bytes], {type: 'audio/webm'}), 'example.webm');
    form.append('model', 'whisper-1');
    form.append('language', 'es');
    const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
      method: 'POST', headers: {'Authorization': `Bearer ${key}`}, body: form, signal: AbortSignal.timeout(30_000),
    });
    if (!response.ok) throw new Error('Transcription service failed');
    const result = await response.json();
    // Do not log audio, transcripts or upstream provider error bodies.
    return new Response(JSON.stringify({text: result.text}), {headers});
  } catch (_) {
    return new Response(JSON.stringify({error: 'Unable to transcribe this example'}), {status: 400, headers});
  }
});
