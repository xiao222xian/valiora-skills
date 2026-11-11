import React, { useMemo } from 'react';
import {
  AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import { BAR, C, CALLOUT_TOP, CAPTION_CENTER_Y, FONT, H, NAMETAG_TOP, SAFE, TAG_TOP, W } from './layout';
import { useFonts } from './fonts';
import type { Insert, Item, Sub, Timeline } from './types';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

// ---------- picture: one continuous mezzanine; alternate punch-in at every jump cut ----------
const VideoLayer: React.FC<{ tl: Timeline }> = ({ tl }) => {
  const frame = useCurrentFrame();
  const pieces = useMemo(() => {
    const out: { start: number; frames: number; scale: number; ox: number; oy: number }[] = [];
    let k = 0;
    for (const it of tl.items) {
      if (it.kind === 'speech') {
        for (const p of it.pieces) {
          const face = p.face;
          // 1.0 / 1.14 alternation hides same-angle jump cuts; close-ups (face wider than 35 % of the frame)
          // only go to 1.07 so the forehead is not cut; pieces without a face (phone demos) get a light 1.06
          const punch = k % 2 === 1 ? (face ? (face.w > 0.35 ? 1.07 : 1.14) : 1.06) : 1.0;
          out.push({ start: p.start, frames: p.frames, scale: punch, ox: face ? face.cx : 0.5, oy: face ? face.cy : 0.45 });
          k += 1;
        }
      } else if (it.kind === 'title') {
        out.push({ start: it.start, frames: it.frames, scale: 1.0, ox: 0.5, oy: 0.5 });
        k = 0;
      } else if (it.kind === 'chapter') {
        k = 0;
      }
    }
    return out;
  }, [tl]);
  const cur = pieces.find((p) => frame >= p.start && frame < p.start + p.frames);
  const prog = cur ? (frame - cur.start) / Math.max(1, cur.frames) : 0;
  const scale = cur ? cur.scale * (1 + 0.035 * prog) : 1;
  return (
    <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#000' }}>
      <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin: `${(cur?.ox ?? 0.5) * 100}% ${(cur?.oy ?? 0.45) * 100}%` }}>
        {/* empty until build_timeline / decorate fill media.video: black placeholder instead of a 404 */}
        {tl.media?.video ? <OffthreadVideo src={staticFile(tl.media.video)} muted style={{ width: W, height: H }} /> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------- title card over a striking close-up from the interview ----------
const TitleCard: React.FC<{ it: Extract<Item, { kind: 'title' }>; tl: Timeline }> = ({ it, tl }) => {
  const frame = useCurrentFrame() - it.start;
  const { fps } = useVideoConfig();
  if (frame < 0 || frame >= it.frames) return null;
  const fadeOut = interpolate(frame, [it.frames - 5, it.frames], [1, 0], clamp);
  const lines = tl.title?.lines ?? [];
  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <AbsoluteFill style={{ background: 'radial-gradient(ellipse at 50% 55%, rgba(10,13,36,0.25) 0%, rgba(10,13,36,0.82) 70%)' }} />
      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: 6, paddingBottom: 80 }}>
        {lines.map((ln, i) => {
          const s = spring({ frame: frame - i * 4, fps, config: { damping: 14, stiffness: 180 } });
          const big = i === lines.length - 1;
          return (
            <div key={i} style={{
              fontFamily: FONT.title, fontSize: big ? 158 : 92, color: big ? C.amber : C.white, lineHeight: 1.12,
              transform: `translateY(${(1 - s) * 40}px) scale(${0.9 + 0.1 * s}) rotate(${big ? -3 : 0}deg)`, opacity: s,
              WebkitTextStroke: big ? `10px ${C.ink}` : `6px ${C.ink}`, paintOrder: 'stroke fill',
              textShadow: big ? `8px 10px 0 ${C.ink}` : `5px 6px 0 ${C.ink}`, letterSpacing: big ? 2 : 4,
            }}>{ln}</div>
          );
        })}
        {tl.title?.byline && (
          <div style={{ marginTop: 34, fontFamily: FONT.sans, fontWeight: 700, fontSize: 36, color: C.glow, letterSpacing: 8,
            opacity: interpolate(frame, [10, 18], [0, 1], clamp) }}>{tl.title.byline}</div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------- chapter card (black) ----------
const ChapterCard: React.FC<{ it: Extract<Item, { kind: 'chapter' }> }> = ({ it }) => {
  const frame = useCurrentFrame() - it.start;
  const { fps } = useVideoConfig();
  if (frame < 0 || frame >= it.frames) return null;
  const s = spring({ frame, fps, config: { damping: 16, stiffness: 200 } });
  const out = interpolate(frame, [it.frames - 4, it.frames], [1, 0], clamp);
  return (
    <AbsoluteFill style={{ backgroundColor: C.ink, justifyContent: 'center', alignItems: 'center', flexDirection: 'column' }}>
      <AbsoluteFill style={{ background: 'radial-gradient(circle at 50% 46%, rgba(76,125,255,0.32) 0%, rgba(10,13,36,0) 55%)' }} />
      <div style={{ opacity: out, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22 }}>
        <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 40, color: C.amber, letterSpacing: 14, opacity: s }}>第{it.index}章</div>
        <div style={{ fontFamily: FONT.title, fontSize: 100, color: C.white, textAlign: 'center', maxWidth: 960, lineHeight: 1.15,
          transform: `scale(${0.88 + 0.12 * s})`, opacity: s }}>{it.title}</div>
        <div style={{ width: interpolate(s, [0, 1], [0, 220]), height: 6, borderRadius: 3, background: C.blue, marginTop: 8 }} />
      </div>
    </AbsoluteFill>
  );
};

// ---------- progress bar: every chapter visible at all times, current chapter and its progress ----------
const ProgressBar: React.FC<{ tl: Timeline }> = ({ tl }) => {
  const frame = useCurrentFrame();
  const chapters = tl.items.filter((i) => i.kind === 'chapter') as Extract<Item, { kind: 'chapter' }>[];
  const outro = tl.items.find((i) => i.kind === 'outro');
  const end = outro ? outro.start : tl.frames;
  if (!chapters.length || frame < chapters[0].start || frame >= end) return null;
  const ranges = chapters.map((c, i) => [c.start, i + 1 < chapters.length ? chapters[i + 1].start : end]);
  const inOp = interpolate(frame, [chapters[0].start + 30, chapters[0].start + 40], [0, 1], clamp);
  const gap = 10;
  const total = W - SAFE.side * 2;
  const segW = (total - gap * (ranges.length - 1)) / ranges.length;
  return (
    <div style={{ position: 'absolute', top: BAR.top, left: SAFE.side, width: total, height: BAR.height, display: 'flex', gap, opacity: inOp }}>
      {ranges.map(([a, b], i) => {
        const p = Math.max(0, Math.min(1, (frame - a) / (b - a)));
        const active = frame >= a && frame < b;
        const done = frame >= b;
        return (
          <div key={i} style={{ width: segW, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 8 }}>
            <div style={{ fontFamily: FONT.sans, fontWeight: active ? 900 : 600, fontSize: 25, whiteSpace: 'nowrap', overflow: 'hidden',
              color: active ? C.amber : done ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.55)', textAlign: 'center',
              textShadow: '0 2px 6px rgba(0,0,0,0.75)' }}>{tl.chapters[i]?.short ?? tl.chapters[i]?.title ?? ''}</div>
            <div style={{ height: 7, borderRadius: 4, background: 'rgba(255,255,255,0.28)', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.5)' }}>
              <div style={{ width: `${(done ? 1 : p) * 100}%`, height: '100%', background: active ? C.amber : 'rgba(255,255,255,0.9)' }} />
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ---------- captions: guest answers big with one highlight; interviewer questions in a question card ----------
const Caption: React.FC<{ subs: Sub[]; hidden: boolean }> = ({ subs, hidden }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const s = subs.find((x) => t >= x.start && t < x.end);
  if (!s || hidden) return null;
  const local = (t - s.start) * fps;
  const pop = interpolate(local, [0, 4], [0.9, 1], clamp);
  if (s.speaker === 'Q') {
    return (
      <div style={{ position: 'absolute', left: 0, right: 0, top: CAPTION_CENTER_Y - 60, display: 'flex', justifyContent: 'center' }}>
        {/* the interviewer's line: a dark card with a glowing left bar, no "提问" label (the card itself marks the speaker) */}
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 20, maxWidth: 980, padding: '20px 32px 20px 22px', borderRadius: 26,
          background: 'rgba(10,13,36,0.84)', border: `3px solid ${C.blue}`, transform: `scale(${pop})`, boxShadow: '0 10px 30px rgba(0,0,0,0.35)' }}>
          <div style={{ flex: 'none', width: 8, borderRadius: 4, background: C.glow, boxShadow: `0 0 14px ${C.glow}` }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 50, color: C.white, lineHeight: 1.25 }}>{s.text}</div>
            {s.en && <div style={{ fontFamily: FONT.sans, fontWeight: 600, fontSize: 32, color: 'rgba(255,255,255,0.85)', lineHeight: 1.2 }}>{s.en}</div>}
          </div>
        </div>
      </div>
    );
  }
  const parts = s.hl && s.text.includes(s.hl) ? s.text.split(s.hl) : null;
  return (
    <div style={{ position: 'absolute', left: 50, right: 50, top: CAPTION_CENTER_Y - 50, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ fontFamily: FONT.sans, fontWeight: 900, fontSize: 70, color: C.white, textAlign: 'center', lineHeight: 1.22,
        WebkitTextStroke: `11px ${C.ink}`, paintOrder: 'stroke fill', textShadow: '0 6px 14px rgba(0,0,0,0.45)', transform: `scale(${pop})`, letterSpacing: 1 }}>
        {parts && parts.length === 2 ? (
          <>{parts[0]}<span style={{ color: C.amber, display: 'inline-block', transform: `scale(${interpolate(local, [0, 5, 9], [1, 1.12, 1.06], clamp)})` }}>{s.hl}</span>{parts[1]}</>
        ) : s.text}
      </div>
      {s.en && (
        <div style={{ marginTop: 6, maxWidth: 940, fontFamily: FONT.sans, fontWeight: 700, fontSize: 38, color: C.white, textAlign: 'center', lineHeight: 1.2,
          WebkitTextStroke: `7px ${C.ink}`, paintOrder: 'stroke fill', textShadow: '0 4px 10px rgba(0,0,0,0.45)' }}>{s.en}</div>
      )}
    </div>
  );
};

// ---------- name tag and location tag ----------
const NameTag: React.FC<{ tl: Timeline }> = ({ tl }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = tl.nametag;
  if (!n || frame < n.start || frame >= n.end) return null;
  const s = spring({ frame: frame - n.start, fps, config: { damping: 15, stiffness: 160 } });
  const out = interpolate(frame, [n.end - 8, n.end], [1, 0], clamp);
  return (
    <div style={{ position: 'absolute', left: 56, top: NAMETAG_TOP, opacity: out, transform: `translateX(${(1 - s) * -80}px)` }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16 }}>
        <div style={{ width: 12, height: 92, background: C.amber, borderRadius: 6 }} />
        <div style={{ fontFamily: FONT.title, fontSize: 96, color: C.white, lineHeight: 1, WebkitTextStroke: `8px ${C.ink}`, paintOrder: 'stroke fill' }}>{n.name}</div>
        {n.en && <div style={{ fontFamily: FONT.sans, fontWeight: 900, fontSize: 52, color: C.amber, WebkitTextStroke: `7px ${C.ink}`, paintOrder: 'stroke fill', marginBottom: 4 }}>{n.en}</div>}
      </div>
      <div style={{ marginTop: 14, marginLeft: 28, display: 'inline-block', fontFamily: FONT.sans, fontWeight: 700, fontSize: 34, color: C.white,
        background: 'rgba(10,13,36,0.82)', padding: '10px 20px', borderRadius: 12, letterSpacing: 2 }}>{n.desc}</div>
    </div>
  );
};

const LocationTag: React.FC<{ tl: Timeline }> = ({ tl }) => {
  const frame = useCurrentFrame();
  const l = tl.location;
  if (!l || frame < l.start || frame >= l.end) return null;
  const op = interpolate(frame, [l.start, l.start + 8, l.end - 8, l.end], [0, 1, 1, 0], clamp);
  return (
    <div style={{ position: 'absolute', left: SAFE.side, top: TAG_TOP, opacity: op, display: 'flex', alignItems: 'center', gap: 12,
      background: 'rgba(10,13,36,0.78)', padding: '10px 20px 10px 16px', borderRadius: 30 }}>
      <div style={{ width: 16, height: 16, borderRadius: 8, background: C.amber, boxShadow: `0 0 12px ${C.amber}` }} />
      <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 30, color: C.white, letterSpacing: 3 }}>{l.text}</div>
    </div>
  );
};

// ---------- explanatory graphics (equation chips at the top; stamp / number / arrow on the chest area) ----------
const CalloutLayer: React.FC<{ tl: Timeline }> = ({ tl }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return (
    <>
      {(tl.callouts ?? []).filter((c) => t >= c.start && t < c.end).map((c, i) => {
        const local = (t - c.start) * fps;
        const out = interpolate(t, [c.end - 0.25, c.end], [1, 0], clamp);
        if (c.kind === 'equation') {
          return (
            <div key={i} style={{ position: 'absolute', top: TAG_TOP + 30, left: SAFE.side, right: SAFE.side, display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 12, opacity: out }}>
              {c.steps.filter((st) => t >= st.at).map((st, k) => {
                const s = spring({ frame: (t - st.at) * fps, fps, config: { damping: 13, stiffness: 220 } });
                const last = st.op === '=' || !!st.hl; // hl: highlight the final step of an arrow sequence (no '=')
                return (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 12, transform: `scale(${0.6 + 0.4 * s})`, opacity: s }}>
                    {st.op && <div style={{ fontFamily: FONT.sans, fontWeight: 900, fontSize: 48, color: C.white, textShadow: '0 2px 8px rgba(0,0,0,0.8)' }}>{st.op}</div>}
                    <div style={{ fontFamily: FONT.sans, fontWeight: 900, fontSize: 42, color: last ? C.ink : C.white, background: last ? C.amber : 'rgba(21,26,74,0.92)',
                      border: `3px solid ${last ? C.amber : C.blue}`, borderRadius: 18, padding: '10px 22px',
                      boxShadow: last ? '0 0 26px rgba(255,194,61,0.6)' : '0 0 22px rgba(76,125,255,0.55)' }}>{st.text}</div>
                  </div>
                );
              })}
            </div>
          );
        }
        if (c.kind === 'stamp') {
          const s = spring({ frame: local, fps, config: { damping: 11, stiffness: 260 } });
          return (
            <div key={i} style={{ position: 'absolute', top: CALLOUT_TOP + 70, left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: out }}>
              <div style={{ fontFamily: FONT.title, fontSize: 112, color: C.amber, padding: '8px 34px', border: `8px solid ${C.amber}`, borderRadius: 22,
                background: 'rgba(10,13,36,0.72)', transform: `rotate(-5deg) scale(${1.5 - 0.5 * s})`, opacity: Math.min(1, s * 1.4), textShadow: `6px 7px 0 ${C.ink}` }}>{c.text}</div>
            </div>
          );
        }
        if (c.kind === 'number') {
          const s = spring({ frame: local, fps, config: { damping: 12, stiffness: 200 } });
          return (
            <div key={i} style={{ position: 'absolute', top: CALLOUT_TOP, left: 0, right: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: out }}>
              <div style={{ display: 'flex', alignItems: 'baseline', transform: `scale(${0.7 + 0.3 * s})`, opacity: s }}>
                <span style={{ fontFamily: FONT.title, fontSize: 190, color: C.amber, WebkitTextStroke: `10px ${C.ink}`, paintOrder: 'stroke fill', textShadow: `8px 10px 0 ${C.ink}` }}>{c.value}</span>
                <span style={{ fontFamily: FONT.title, fontSize: 96, color: C.white, WebkitTextStroke: `8px ${C.ink}`, paintOrder: 'stroke fill', marginLeft: 6 }}>{c.unit}</span>
              </div>
              <div style={{ marginTop: 4, fontFamily: FONT.sans, fontWeight: 800, fontSize: 38, color: C.white, background: 'rgba(10,13,36,0.85)', padding: '8px 22px', borderRadius: 12,
                opacity: interpolate(local, [6, 12], [0, 1], clamp) }}>{c.label}</div>
            </div>
          );
        }
        const s = spring({ frame: local, fps, config: { damping: 14, stiffness: 180 } });
        const s2 = spring({ frame: local - 8, fps, config: { damping: 14, stiffness: 180 } });
        return (
          <div key={i} style={{ position: 'absolute', top: CALLOUT_TOP + 40, left: 0, right: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, opacity: out }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 26 }}>
              <span style={{ fontFamily: FONT.title, fontSize: 150, color: C.white, opacity: s, WebkitTextStroke: `9px ${C.ink}`, paintOrder: 'stroke fill' }}>{c.from}</span>
              <div style={{ width: interpolate(s2, [0, 1], [0, 170]), height: 14, background: C.amber, borderRadius: 7, position: 'relative' }}>
                <div style={{ position: 'absolute', right: -6, top: -15, width: 0, height: 0, borderTop: '22px solid transparent', borderBottom: '22px solid transparent', borderLeft: `34px solid ${C.amber}`, opacity: s2 }} />
              </div>
              <span style={{ fontFamily: FONT.title, fontSize: 150, color: C.amber, opacity: s2, WebkitTextStroke: `9px ${C.ink}`, paintOrder: 'stroke fill' }}>{c.to}</span>
            </div>
            <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 36, color: C.white, background: 'rgba(10,13,36,0.85)', padding: '8px 22px', borderRadius: 12, opacity: s2 }}>{c.label}</div>
          </div>
        );
      })}
    </>
  );
};

// ---------- every insert (B-roll clip, reference card, album, photo) covers frames round(start * fps) .. round(end * fps) ----------
// start / end are seconds rounded to 3 decimals (decorate.py), so a start on a frame boundary can land just after it
// (frame 4538 = 151.2667 s -> 151.267): comparing frame / fps with it showed the photo one frame late, black over the outro
const span = (ins: Insert, fps: number): [number, number] => {
  const from = Math.round(ins.start * fps);
  return [from, Math.round(ins.end * fps) - from];
};

// ---------- B-roll insert: the guest's own product footage, full screen, short dissolves, slow push-in ----------
const BrollBody: React.FC<{ ins: Insert; dur: number }> = ({ ins, dur }) => {
  const local = useCurrentFrame(); // frames since the insert started (inside its Sequence)
  const { fps } = useVideoConfig();
  const op = interpolate(local, [0, 4, dur - 4, dur], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{ opacity: op, overflow: 'hidden', backgroundColor: '#000' }}>
      <OffthreadVideo src={staticFile(ins.img)} startFrom={Math.round((ins.from ?? 0) * fps)} muted
        style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.02 + 0.04 * (local / dur)})` }} />
    </AbsoluteFill>
  );
};

// a Sequence so the clip's own time starts at the insert (OffthreadVideo plays from the Sequence start)
const BrollInsert: React.FC<{ ins: Insert }> = ({ ins }) => {
  const { fps } = useVideoConfig();
  const [from, dur] = span(ins, fps);
  return (
    <Sequence from={from} durationInFrames={dur} layout="none">
      <BrollBody ins={ins} dur={dur} />
    </Sequence>
  );
};

// ---------- concept reference: picture + name + one line, over a blurred copy; captions stay on top ----------
const REF = { labelTop: 250, cardTop: 470, maxW: 940, maxH: 800 }; // card ends above the caption band (y≈1345)
const RefCard: React.FC<{ ins: Insert }> = ({ ins }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [from, dur] = span(ins, fps);
  const local = frame - from;
  if (local < 0 || local >= dur || !ins.ref) return null;
  const op = interpolate(local, [0, 4, dur - 4, dur], [0, 1, 1, 0], clamp);
  const s = spring({ frame: local, fps, config: { damping: 16, stiffness: 190 } });
  const a = ins.ref.ar; // width / height of the image, written into the package (async onLoad is not safe in a render)
  const w = Math.min(REF.maxW, REF.maxH * a);
  const h = w / a;
  const r = ins.ref;
  const stack = r.name.length + (r.sub?.length ?? 0) / 2 > 14;
  return (
    <AbsoluteFill style={{ opacity: op }}>
      <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: C.ink }}>
        <Img src={staticFile(ins.img)} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(44px) brightness(0.42)', transform: 'scale(1.25)' }} />
      </AbsoluteFill>
      <div style={{ position: 'absolute', top: REF.labelTop, left: 60, right: 60, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
        transform: `translateY(${(1 - s) * -24}px)` }}>
        {/* a long name (第四代关系空间) and its English sub do not fit side by side: stack them instead of wrapping the name */}
        <div style={{ display: 'flex', flexDirection: stack ? 'column' : 'row', alignItems: stack ? 'center' : 'baseline', gap: stack ? 8 : 18 }}>
          <span style={{ fontFamily: FONT.title, fontSize: 84, color: C.amber, lineHeight: 1, whiteSpace: 'nowrap', WebkitTextStroke: `8px ${C.ink}`, paintOrder: 'stroke fill' }}>{r.name}</span>
          {r.sub && <span style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 40, color: C.white, WebkitTextStroke: `6px ${C.ink}`, paintOrder: 'stroke fill' }}>{r.sub}</span>}
        </div>
        <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 34, color: 'rgba(255,255,255,0.92)', textAlign: 'center', lineHeight: 1.3 }}>{r.desc}</div>
      </div>
      <div style={{ position: 'absolute', top: REF.cardTop + (REF.maxH - h) / 2, left: (1080 - w) / 2, width: w, height: h, borderRadius: 22, overflow: 'hidden',
        border: '4px solid rgba(255,255,255,0.9)', boxShadow: '0 30px 60px rgba(0,0,0,0.5)', transform: `scale(${0.94 + 0.06 * s})` }}>
        <Img src={staticFile(ins.img)}
          style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1 + 0.05 * (local / dur)})` }} />
      </div>
      <div style={{ position: 'absolute', top: REF.cardTop + (REF.maxH + h) / 2 + 12, left: 0, right: 0, textAlign: 'center',
        fontFamily: FONT.sans, fontWeight: 500, fontSize: 22, color: 'rgba(255,255,255,0.6)' }}>{r.credit}</div>
    </AbsoluteFill>
  );
};

// ---------- album: the guest's own photos dropped one by one onto a pile of white-bordered cards ----------
// The photo card below is 16:9 (group photos) and cuts a portrait photo down to a strip. Each card lands on top with its
// own tilt and its blurred copy fades in behind the pile, so the earlier cards stay visible underneath. The pile sits
// between the progress bar and the caption band; the name tag and location tag leave before the album starts.
const ALBUM = { top: TAG_TOP, bottom: 1290, maxW: 840, pad: 14 }; // cards end above the caption band (y≈1345)
const TILT = [-4, 3, -2.5, 4, -3];
const NUDGE = [[-16, 8], [18, -6], [-10, 12], [14, 2], [-4, -8]];
const AlbumInsert: React.FC<{ ins: Insert }> = ({ ins }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const album = ins.album ?? [];
  const [from, dur] = span(ins, fps);
  const local = frame - from;
  if (local < 0 || local >= dur || album.length === 0) return null;
  const step = dur / album.length; // frames per photo
  const op = interpolate(local, [0, 4, dur - 4, dur], [0, 1, 1, 0], clamp);
  const shown = album.slice(0, Math.min(album.length, Math.floor(local / step) + 1));
  const maxH = ALBUM.bottom - ALBUM.top;
  return (
    <AbsoluteFill style={{ opacity: op }}>
      {shown.map((p, k) => (
        <AbsoluteFill key={`bg${k}`} style={{ overflow: 'hidden', opacity: interpolate(local - k * step, [0, 5], [0, 1], clamp) }}>
          <Img src={staticFile(p.img)} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(40px) brightness(0.5)', transform: 'scale(1.2)' }} />
        </AbsoluteFill>
      ))}
      {shown.map((p, k) => {
        const since = local - k * step;
        const s = spring({ frame: since, fps, config: { damping: 15, stiffness: 170 } });
        const iw = Math.min(ALBUM.maxW, (maxH - 2 * ALBUM.pad) * p.ar); // the picture keeps the photo's own aspect
        const ih = iw / p.ar;
        const [nx, ny] = NUDGE[k % NUDGE.length];
        const [fx, fy] = p.focus ?? [0.5, 0.4];
        return (
          <div key={`card${k}`} style={{ position: 'absolute', left: (W - iw) / 2 - ALBUM.pad + nx, top: ALBUM.top + (maxH - ih) / 2 - ALBUM.pad + ny,
            background: '#fff', padding: ALBUM.pad, borderRadius: 10, boxShadow: '0 30px 60px rgba(0,0,0,0.5)', opacity: Math.min(1, s * 1.6),
            transform: `translateY(${(1 - s) * 90}px) rotate(${TILT[k % TILT.length] + (1 - s) * 6}deg) scale(${0.92 + 0.08 * s})` }}>
            <div style={{ width: iw, height: ih, overflow: 'hidden', borderRadius: 4 }}>
              <Img src={staticFile(p.img)} style={{ width: '100%', height: '100%', objectFit: 'cover',
                transform: `scale(${1 + 0.04 * Math.min(1, since / (step * 1.5))})`, transformOrigin: `${fx * 100}% ${fy * 100}%` }} />
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------- photo insert: white-bordered card over a blurred copy (behind-the-scenes, group photo) ----------
const PhotoInsert: React.FC<{ ins: Insert }> = ({ ins }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (ins.video) return <BrollInsert ins={ins} />;
  if (ins.ref) return <RefCard ins={ins} />;
  if (ins.album) return <AlbumInsert ins={ins} />;
  const [from, dur] = span(ins, fps);
  const local = frame - from;
  if (local < 0 || local >= dur) return null;
  const s = spring({ frame: local, fps, config: { damping: 15, stiffness: 170 } });
  const zoom = 1 + 0.05 * (local / dur);
  const flash = ins.flash ? interpolate(local, [0, 2, 9], [0, 0.9, 0], clamp) : 0;
  const [fx, fy] = ins.focus ?? [0.5, 0.5];
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ overflow: 'hidden' }}>
        <Img src={staticFile(ins.img)} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(40px) brightness(0.55)', transform: 'scale(1.2)' }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ width: 1000, background: '#fff', padding: 16, borderRadius: 10, boxShadow: '0 30px 60px rgba(0,0,0,0.5)',
          transform: `translateY(${(1 - s) * 60 - 120}px) rotate(${(1 - s) * 4 - 1.5}deg)`, opacity: s }}>
          <div style={{ width: '100%', aspectRatio: '16 / 9', overflow: 'hidden', borderRadius: 4 }}>
            <Img src={staticFile(ins.img)} style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zoom})`, transformOrigin: `${fx * 100}% ${fy * 100}%` }} />
          </div>
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ backgroundColor: '#fff', opacity: flash }} />
    </AbsoluteFill>
  );
};

// ---------- official logo end card (public/img/logo.png, white version) ----------
const LogoCard: React.FC<{ start: number; frames: number }> = ({ start, frames }) => {
  const frame = useCurrentFrame() - start;
  if (frame < 0 || frame >= frames) return null;
  const op = interpolate(frame, [0, 10, frames - 8, frames], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{ backgroundColor: C.ink, justifyContent: 'center', alignItems: 'center' }}>
      <AbsoluteFill style={{ background: 'radial-gradient(circle at 50% 50%, rgba(76,125,255,0.28) 0%, rgba(10,13,36,0) 55%)' }} />
      <Img src={staticFile('img/logo.png')} style={{ width: 560, opacity: op, transform: `scale(${0.96 + 0.04 * op})` }} />
    </AbsoluteFill>
  );
};

export const Film: React.FC<{ tl: Timeline; subs: Sub[] }> = ({ tl, subs }) => {
  useFonts();
  const frame = useCurrentFrame();
  const title = tl.items.find((i) => i.kind === 'title') as Extract<Item, { kind: 'title' }> | undefined;
  const chapters = tl.items.filter((i) => i.kind === 'chapter') as Extract<Item, { kind: 'chapter' }>[];
  const outro = tl.items.find((i) => i.kind === 'outro') as Extract<Item, { kind: 'outro' }> | undefined;
  const inCard = (title && frame >= title.start && frame < title.start + title.frames)
    || chapters.some((c) => frame >= c.start && frame < c.start + c.frames)
    || (outro && frame >= outro.start);
  const logoFrames = tl.logo_frames ?? 54;
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      <VideoLayer tl={tl} />
      {(tl.inserts ?? []).map((ins, i) => <PhotoInsert key={i} ins={ins} />)}
      <CalloutLayer tl={tl} />
      <LocationTag tl={tl} />
      <NameTag tl={tl} />
      <ProgressBar tl={tl} />
      <Caption subs={subs} hidden={!!inCard} />
      {title && <TitleCard it={title} tl={tl} />}
      {chapters.map((c) => <ChapterCard key={c.chapter} it={c} />)}
      {/* lov-logo-sting outro (optional, SKILL.md Step 6): copy its LogoSting.tsx into src/ and spec / timing into src/data/,
          then replace this line with <Sequence from={outro.start + outro.frames - timing.dur} durationInFrames={timing.dur}>
          <LogoSting spec={spec} timing={timing} intro="black" /></Sequence>; sting.wav goes into the final mix, not here */}
      {outro && <LogoCard start={outro.start + outro.frames - logoFrames} frames={logoFrames} />}
      {tl.media?.audio && <Audio src={staticFile(tl.media.audio)} />}
    </AbsoluteFill>
  );
};
