/**
 * useSpeech — narrate lesson text aloud, cheapest-good-voice-first.
 *
 * Tries the backend Edge neural voice (free, natural — the male "Andrew" voice)
 * first; if that route is unavailable or blocked, it falls back automatically to
 * the browser's built-in Web Speech API (free, offline, no key). Same play/stop
 * button either way — matching Titan Track's "always degrade, never hard-fail".
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { titan } from '../../services/apiService';

// ── Autoplay unlock ──────────────────────────────────────────────────────────
// Browsers block audio that starts OUTSIDE a user gesture. Our narration starts
// AFTER an `await` (the TTS fetch), which outlives the click's activation window
// — so both the fetched clip AND the Web-Speech fallback get silently blocked
// (you hear nothing, no error). We defeat that once: on the first real
// interaction we play a 44-byte silent WAV and prime speechSynthesis, which
// grants the page audio permission for everything that follows.
let _unlockInstalled = false;
let _synthPrimed = false;

function silentWavUrl() {
  // A valid, silent, zero-sample 16-bit/44.1k mono WAV — built in JS so there's
  // no chance of a bad hand-typed base64 string.
  const b = new Uint8Array([
    0x52, 0x49, 0x46, 0x46, 0x24, 0, 0, 0, 0x57, 0x41, 0x56, 0x45,
    0x66, 0x6d, 0x74, 0x20, 0x10, 0, 0, 0, 1, 0, 1, 0,
    0x44, 0xac, 0, 0, 0x88, 0x58, 1, 0, 2, 0, 0x10, 0,
    0x64, 0x61, 0x74, 0x61, 0, 0, 0, 0,
  ]);
  return URL.createObjectURL(new Blob([b], { type: 'audio/wav' }));
}

let _silentUrl = null;
function getSilentUrl() {
  if (typeof window === 'undefined') return '';
  if (!_silentUrl) _silentUrl = silentWavUrl();
  return _silentUrl;
}

function installUnlock() {
  if (_unlockInstalled || typeof window === 'undefined') return;
  _unlockInstalled = true;
  const events = ['pointerdown', 'keydown', 'touchstart'];
  const go = () => {
    try {
      const silent = new Audio(silentWavUrl());
      silent.play().then(() => silent.pause()).catch(() => {});
    } catch { /* noop */ }
    if (window.speechSynthesis && !_synthPrimed) {
      try {
        const u = new SpeechSynthesisUtterance(' ');
        u.volume = 0;
        window.speechSynthesis.speak(u);
        window.speechSynthesis.cancel();
        _synthPrimed = true;
      } catch { /* noop */ }
    }
    events.forEach((ev) => window.removeEventListener(ev, go, { capture: true }));
  };
  events.forEach((ev) => window.addEventListener(ev, go, { capture: true, passive: true }));
}

// Best English voice for the browser fallback — prefer a male one so it matches
// the Edge "Andrew" voice the backend uses.
function pickVoice() {
  const v = (typeof window !== 'undefined' && window.speechSynthesis?.getVoices?.()) || [];
  if (!v.length) return null;
  const male = v.find(
    (x) => /guy|andrew|christopher|eric|david|mark|ryan|aaron|male/i.test(x.name) && /^en/i.test(x.lang),
  );
  return male || v.find((x) => /^en/i.test(x.lang)) || v[0];
}

// Split prose into ~180-char pieces on sentence boundaries. Narrating the first
// short piece starts audio in well under a second instead of waiting for the
// whole step to synthesize server-side.
function chunkText(text, target = 180) {
  const sentences = text.match(/[^.!?]+[.!?]*\s*/g) || [text];
  const out = [];
  let cur = '';
  for (const s of sentences) {
    if (cur && (cur.length + s.length) > target) { out.push(cur.trim()); cur = s; }
    else cur += s;
  }
  if (cur.trim()) out.push(cur.trim());
  return out.length ? out : [text];
}

export function useSpeech() {
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef(null);
  const cancelRef = useRef(false); // set when the user hits Stop mid-fetch

  useEffect(() => {
    installUnlock();
    // Chromium populates the voice list asynchronously — warm it so the fallback
    // has a voice ready.
    const warm = () => window.speechSynthesis?.getVoices();
    warm();
    window.speechSynthesis?.addEventListener?.('voiceschanged', warm);
    return () => window.speechSynthesis?.removeEventListener?.('voiceschanged', warm);
  }, []);

  const stop = useCallback(() => {
    cancelRef.current = true;
    if (audioRef.current) {
      try { audioRef.current.pause(); } catch { /* noop */ }
      if (audioRef.current.src?.startsWith('blob:')) URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
    }
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      try { window.speechSynthesis.cancel(); } catch { /* noop */ }
    }
    setSpeaking(false);
  }, []);

  // Browser fallback — chunk into sentences to dodge Chrome's ~250-char cutoff.
  const speakBrowser = useCallback((text) => {
    const synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
    if (!synth) { setSpeaking(false); toast.error('Narration is not available in this browser.'); return; }
    try { synth.cancel(); } catch { /* noop */ }
    const voice = pickVoice();
    const parts = text.match(/[^.!?]+[.!?]*\s*/g) || [text];
    let i = 0;
    const next = () => {
      if (cancelRef.current || i >= parts.length) { setSpeaking(false); return; }
      const u = new SpeechSynthesisUtterance(parts[i].trim());
      if (voice) u.voice = voice;
      u.rate = 1.0;
      u.pitch = 1.0;
      u.onend = () => { i += 1; next(); };
      u.onerror = () => { i += 1; next(); };
      synth.speak(u);
    };
    setSpeaking(true);
    try { synth.resume(); } catch { /* noop */ } // nudge Chromium out of a stuck 'paused' state
    next();
  }, []);

  const speak = useCallback(async (text) => {
    const clean = (text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return;
    stop();
    cancelRef.current = false;
    setSpeaking(true);

    // Sentence-chunked streaming: synthesize + play the first short piece fast,
    // and prefetch the following pieces while it talks — so audio starts in
    // well under a second instead of after the whole step synthesizes.
    const chunks = chunkText(clean, 180);
    const fetches = new Array(chunks.length).fill(null);
    const fetchChunk = (i) => {
      if (i < 0 || i >= chunks.length) return null;
      if (!fetches[i]) {
        fetches[i] = titan.tts(chunks[i])
          .then((buf) => (buf && buf.byteLength ? URL.createObjectURL(new Blob([buf], { type: 'audio/mpeg' })) : null))
          .catch(() => null);
      }
      return fetches[i];
    };

    // One audio element, unlocked by a silent play inside this click gesture so
    // the fetched clips are allowed to play even though the fetch outlives it.
    const audio = new Audio(getSilentUrl());
    audio.preload = 'auto';
    audioRef.current = audio;
    await audio.play().catch(() => { /* noop */ });

    const playFrom = async (i) => {
      if (cancelRef.current) return;
      if (i >= chunks.length) { audioRef.current = null; setSpeaking(false); return; }
      fetchChunk(i);
      fetchChunk(i + 1); // prefetch the next piece while this one plays
      const url = await fetchChunk(i);
      if (cancelRef.current) return;
      if (!url) { speakBrowser(chunks.slice(i).join(' ')); return; } // synth failed → browser voice for the rest
      audio.src = url;
      audio.onended = () => { URL.revokeObjectURL(url); playFrom(i + 1); };
      audio.onerror = () => { URL.revokeObjectURL(url); if (!cancelRef.current) speakBrowser(chunks.slice(i).join(' ')); };
      try { await audio.play(); }
      catch { URL.revokeObjectURL(url); if (!cancelRef.current) speakBrowser(chunks.slice(i).join(' ')); }
    };
    playFrom(0);
  }, [stop, speakBrowser]);

  // Warm the cache for a step's first sentence when it's shown, so hitting
  // Listen starts almost instantly instead of waiting on a fresh synthesis +
  // connection round-trip to Microsoft's server.
  const prefetch = useCallback((text) => {
    const clean = (text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return;
    const first = chunkText(clean, 180)[0];
    if (first) titan.tts(first).catch(() => { /* best-effort warm-up */ });
  }, []);

  useEffect(() => () => stop(), [stop]);

  // Narration is possible if either path exists. Audio is universal in-browser;
  // speechSynthesis is the fallback. Hidden during SSR.
  const supported = typeof window !== 'undefined' &&
    (typeof window.Audio !== 'undefined' || !!window.speechSynthesis);

  return { speak, stop, speaking, supported, prefetch };
}
