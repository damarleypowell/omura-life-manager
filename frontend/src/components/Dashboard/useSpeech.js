/**
 * useSpeech — narrate lesson text aloud, cheapest-good-voice-first.
 *
 * Tries the backend Edge neural voice (free, natural) first; if that route is
 * unavailable or errors, it falls back automatically to the browser's built-in
 * Web Speech API (free, offline, no key). Same play/stop button either way —
 * matching the rest of Titan Track's "always degrade, never hard-fail" style.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { titan } from '../../services/apiService';

export function useSpeech() {
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef(null);
  const cancelRef = useRef(false); // set when the user hits Stop mid-fetch

  const stop = useCallback(() => {
    cancelRef.current = true;
    if (audioRef.current) {
      try { audioRef.current.pause(); } catch { /* noop */ }
      if (audioRef.current.src?.startsWith('blob:')) URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
    }
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setSpeaking(false);
  }, []);

  // Browser fallback — chunk into sentences to dodge Chrome's ~250-char cutoff.
  const speakBrowser = useCallback((text) => {
    const synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
    if (!synth) { setSpeaking(false); return; }
    synth.cancel();
    const parts = text.match(/[^.!?]+[.!?]*\s*/g) || [text];
    let i = 0;
    const next = () => {
      if (cancelRef.current || i >= parts.length) { setSpeaking(false); return; }
      const u = new SpeechSynthesisUtterance(parts[i].trim());
      u.rate = 1.0;
      u.pitch = 1.0;
      u.onend = () => { i += 1; next(); };
      u.onerror = () => { i += 1; next(); };
      synth.speak(u);
    };
    setSpeaking(true);
    next();
  }, []);

  const speak = useCallback(async (text) => {
    const clean = (text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return;
    stop();
    cancelRef.current = false;
    setSpeaking(true);

    // 1) Try the better backend (Edge neural) voice.
    try {
      const buf = await titan.tts(clean);
      if (cancelRef.current) return;
      const blob = new Blob([buf], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { URL.revokeObjectURL(url); audioRef.current = null; setSpeaking(false); };
      audio.onerror = () => { URL.revokeObjectURL(url); audioRef.current = null; speakBrowser(clean); };
      await audio.play();
    } catch {
      // 2) Backend unavailable → browser voice.
      if (!cancelRef.current) speakBrowser(clean);
    }
  }, [stop, speakBrowser]);

  useEffect(() => () => stop(), [stop]);

  // Narration is possible if either path exists. Audio is universal in-browser;
  // speechSynthesis is the fallback. Hidden during SSR.
  const supported = typeof window !== 'undefined' &&
    (typeof window.Audio !== 'undefined' || !!window.speechSynthesis);

  return { speak, stop, speaking, supported };
}
