"use client";

import { useEffect, useRef, useCallback } from "react";

const COLORS = [
  [145, 65, 255],
  [100, 70, 235],
  [65, 105, 225],
  [40, 165, 215],
] as const;

const USER_COLOR: readonly [number, number, number] = [255, 255, 255];

const NAMES = [
  "Alex K.", "Sarah M.", "David L.", "Emma R.",
  "James W.", "Maria G.", "Chen W.", "Priya S.",
  "Jordan T.", "Lucas P.", "Ava H.", "Noah C.",
  "Sofia B.", "Ethan J.", "Mia F.", "Liam D.",
];

interface Particle {
  angle: number;
  orbitRadius: number;
  speed: number;
  wobbleAmp: number;
  wobbleSpeed: number;
  wobblePhase: number;
  x: number;
  y: number;
  baseRadius: number;
  radius: number;
  color: readonly [number, number, number];
  alpha: number;
  targetAlpha: number;
  recognized: boolean;
  recognizedAt: number;
  isUser: boolean;
}

interface Pulse {
  x: number;
  y: number;
  startTime: number;
  color: readonly [number, number, number];
}

interface Label {
  text: string;
  x: number;
  y: number;
  startTime: number;
}

interface Tag {
  text: string;
  particle: Particle;
  createdAt: number;
}

const MEETING_DIST = 90;
const APPROACHING_DIST = MEETING_DIST * 1.8;
const CONNECTION_DIST = 160;
const MIN_RECOGNIZED = 6;
const RECOGNITION_LIFETIME = 12000;
const PULSE_DURATION = 1400;
const LABEL_DURATION = 2400;
const RECOGNITION_GAP = 1400;

interface AuroraProps {
  className?: string;
  /** "full" = welcome page (viewfinder, HUD, recognition). "focused" = inner pages (subtle, 20 particles). "ambient" = onboarding (70 particles, no HUD). */
  mode?: "full" | "focused" | "ambient";
  /** Reports user particle position as percentage (0-1) of the canvas. Called each frame. */
  onUserPosition?: (xPct: number, yPct: number) => void;
}

export function Aurora({ className = "", mode = "full", onUserPosition }: AuroraProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const onUserPositionRef = useRef(onUserPosition);
  onUserPositionRef.current = onUserPosition;

  const isFocused = mode === "focused";
  const PARTICLE_COUNT = isFocused ? 20 : 70; // ambient + full both get 70

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const focused = mode === "focused";
    const ambient = mode === "ambient";

    function resize() {
      canvas!.width = Math.round(canvas!.clientWidth * dpr);
      canvas!.height = Math.round(canvas!.clientHeight * dpr);
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    const W = () => canvas!.clientWidth;
    const H = () => canvas!.clientHeight;

    const particleCount = focused ? 20 : 70;
    const particles: Particle[] = [];

    particles.push({
      angle: Math.random() * Math.PI * 2,
      orbitRadius: focused ? 5 : 60 + Math.random() * 80,
      speed: focused ? 0.0001 : 0.00035 * (Math.random() < 0.5 ? 1 : -1),
      wobbleAmp: focused ? 6 : 20 + Math.random() * 15,
      wobbleSpeed: 0.15 + Math.random() * 0.1,
      wobblePhase: Math.random() * Math.PI * 2,
      x: 0, y: 0,
      baseRadius: 3.5,
      radius: 3.5,
      color: USER_COLOR,
      alpha: 1,
      targetAlpha: 1,
      recognized: true,
      recognizedAt: -99999,
      isUser: true,
    });

    for (let i = 1; i < particleCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const orbitRadius = focused
        ? 30 + Math.random() * 100
        : 20 + Math.pow(Math.random(), 0.5) * 300;
      const color = COLORS[Math.floor(Math.random() * COLORS.length)];
      const preRecognized = (focused || ambient) ? true : i <= MIN_RECOGNIZED;

      particles.push({
        angle,
        orbitRadius,
        speed: (0.00008 + Math.random() * 0.0003) * (Math.random() < 0.5 ? 1 : -1),
        wobbleAmp: focused ? 3 + Math.random() * 8 : 4 + Math.random() * 14,
        wobbleSpeed: 0.2 + Math.random() * 0.4,
        wobblePhase: Math.random() * Math.PI * 2,
        x: 0, y: 0,
        baseRadius: 1.2 + Math.random() * 0.6,
        radius: preRecognized ? 2.8 : 1.2 + Math.random() * 0.6,
        color,
        alpha: preRecognized ? (focused ? 0.5 : ambient ? 0.65 : 0.85) : 0.22 + Math.random() * 0.10,
        targetAlpha: preRecognized ? (focused ? 0.5 : ambient ? 0.65 : 0.85) : 0.22 + Math.random() * 0.10,
        recognized: preRecognized,
        recognizedAt: preRecognized ? -RECOGNITION_LIFETIME * 0.3 : 0,
        isUser: false,
      });
    }

    const user = particles[0];
    const pulses: Pulse[] = [];
    const labels: Label[] = [];
    const tags: Tag[] = [];
    let lastRecognition = -RECOGNITION_GAP;
    let nameIdx = Math.floor(Math.random() * NAMES.length);
    let lastFrame = 0;
    let seeded = false;

    function nextName(): string {
      nameIdx = (nameIdx + 1 + Math.floor(Math.random() * 3)) % NAMES.length;
      return NAMES[nameIdx];
    }

    function recognizeParticle(p: Particle, now: number) {
      if (p.recognized || p.isUser) return;
      p.recognized = true;
      p.recognizedAt = now;
      p.targetAlpha = 0.85;
      const mx = (user.x + p.x) / 2;
      const my = (user.y + p.y) / 2;
      pulses.push({ x: mx, y: my, startTime: now, color: p.color });
      const name = nextName();
      labels.push({ text: name, x: p.x, y: p.y, startTime: now });
      tags.push({ text: name, particle: p, createdAt: now });
      lastRecognition = now;
    }

    function seedInitialLabels(now: number) {
      const rec = particles.filter(p => p.recognized && !p.isUser);
      const count = focused ? Math.min(4, rec.length) : Math.min(3, rec.length);
      for (let i = 0; i < count; i++) {
        const p = rec[i];
        const name = nextName();
        labels.push({ text: name, x: p.x, y: p.y, startTime: now + i * 400 });
        tags.push({ text: name, particle: p, createdAt: now + i * 400 });
      }
      if (rec.length >= 2) {
        const mx = (rec[0].x + rec[1].x) / 2;
        const my = (rec[0].y + rec[1].y) / 2;
        pulses.push({ x: mx, y: my, startTime: now + 100, color: rec[0].color });
      }
    }

    function render(now: number) {
      rafRef.current = requestAnimationFrame(render);
      if (now - lastFrame < 33) return;
      const dt = now - lastFrame;
      lastFrame = now;

      const width = W();
      const height = H();
      const centerX = width / 2;
      const centerY = focused ? height * 0.42 : ambient ? height * 0.40 : height * 0.35;

      ctx!.clearRect(0, 0, width, height);

      // Background glow
      const bg1 = ctx!.createRadialGradient(centerX, height * 0.4, 0, centerX, height * 0.4, height * 0.85);
      bg1.addColorStop(0, `rgba(100, 50, 200, ${focused ? 0.10 : 0.16})`);
      bg1.addColorStop(0.35, `rgba(80, 40, 180, ${focused ? 0.06 : 0.10})`);
      bg1.addColorStop(0.65, `rgba(55, 30, 150, ${focused ? 0.03 : 0.06})`);
      bg1.addColorStop(1, "rgba(30, 20, 100, 0.02)");
      ctx!.fillStyle = bg1;
      ctx!.fillRect(0, 0, width, height);

      if (!focused) {
        const bg2 = ctx!.createRadialGradient(width * 0.6, height * 0.65, 0, width * 0.6, height * 0.65, height * 0.5);
        bg2.addColorStop(0, "rgba(60, 40, 180, 0.08)");
        bg2.addColorStop(0.5, "rgba(40, 30, 150, 0.04)");
        bg2.addColorStop(1, "rgba(20, 15, 80, 0)");
        ctx!.fillStyle = bg2;
        ctx!.fillRect(0, 0, width, height);

        const bg3 = ctx!.createRadialGradient(width * 0.35, height * 0.8, 0, width * 0.35, height * 0.8, height * 0.4);
        bg3.addColorStop(0, "rgba(70, 30, 160, 0.06)");
        bg3.addColorStop(1, "rgba(30, 15, 100, 0)");
        ctx!.fillStyle = bg3;
        ctx!.fillRect(0, 0, width, height);
      }

      // Update positions
      for (const p of particles) {
        p.angle += p.speed * dt;
        const wx = Math.sin(now * 0.001 * p.wobbleSpeed + p.wobblePhase) * p.wobbleAmp;
        const wy = Math.cos(now * 0.0008 * p.wobbleSpeed + p.wobblePhase + 1.5) * p.wobbleAmp * 0.6;
        p.x = centerX + Math.cos(p.angle) * p.orbitRadius + wx;
        p.y = centerY + Math.sin(p.angle) * p.orbitRadius * 0.7 + wy;
        p.alpha += (p.targetAlpha - p.alpha) * 0.04;
        if (p.isUser) {
          p.radius = 3.5;
        } else {
          p.radius += ((p.recognized ? 2.8 : p.baseRadius) - p.radius) * 0.04;
        }
      }

      // Report user position to parent
      if (onUserPositionRef.current && width > 0 && height > 0) {
        onUserPositionRef.current(user.x / width, user.y / height);
      }

      if (!seeded) {
        if (ambient) {
          // Seed name tags on every ~10th particle — visible immediately, no floating phase
          const rec = particles.filter(p => p.recognized && !p.isUser);
          const step = Math.max(1, Math.floor(rec.length / 6));
          for (let i = 0; i < rec.length; i += step) {
            tags.push({ text: nextName(), particle: rec[i], createdAt: now - LABEL_DURATION - 300 });
          }
        } else {
          seedInitialLabels(now);
        }
        seeded = true;
      }

      // Recognition (full mode only)
      if (!focused && !ambient) {
        if (now - lastRecognition > RECOGNITION_GAP) {
          const meetSq = MEETING_DIST * MEETING_DIST;
          let closest: Particle | null = null;
          let closestDist = Infinity;
          for (let i = 1; i < particles.length; i++) {
            const p = particles[i];
            if (p.recognized) continue;
            const dx = user.x - p.x;
            const dy = user.y - p.y;
            const d = dx * dx + dy * dy;
            if (d < meetSq && d < closestDist) { closestDist = d; closest = p; }
          }
          if (closest) recognizeParticle(closest, now);
        }

        // Age out
        let recCount = 0;
        for (const p of particles) if (p.recognized && !p.isUser) recCount++;
        for (const p of particles) {
          if (p.isUser) continue;
          if (p.recognized && p.recognizedAt > 0 && now - p.recognizedAt > RECOGNITION_LIFETIME && recCount > MIN_RECOGNIZED) {
            p.recognized = false;
            p.targetAlpha = 0.22 + Math.random() * 0.10;
            p.recognizedAt = 0;
            recCount--;
          }
        }

        // Approaching indicators
        const approachSq = APPROACHING_DIST * APPROACHING_DIST;
        ctx!.save();
        ctx!.setLineDash([4, 5]);
        for (let i = 1; i < particles.length; i++) {
          const p = particles[i];
          if (p.recognized) continue;
          const dx = user.x - p.x;
          const dy = user.y - p.y;
          const dSq = dx * dx + dy * dy;
          if (dSq > approachSq) continue;
          const dist = Math.sqrt(dSq);
          const proximity = 1 - dist / APPROACHING_DIST;
          p.radius += (p.baseRadius * (1 + proximity * 0.8) - p.radius) * 0.08;
          p.alpha += ((0.08 + proximity * 0.25) - p.alpha) * 0.06;
          ctx!.strokeStyle = `rgba(180, 140, 255, ${proximity * 0.12})`;
          ctx!.lineWidth = 0.6;
          ctx!.beginPath();
          ctx!.moveTo(user.x, user.y);
          ctx!.lineTo(p.x, p.y);
          ctx!.stroke();
        }
        ctx!.restore();
      }

      // Connections from user to recognized
      const connDist = focused ? 200 : CONNECTION_DIST;
      const connSq = connDist * connDist;
      for (let i = 1; i < particles.length; i++) {
        const p = particles[i];
        if (!p.recognized) continue;
        const dx = user.x - p.x;
        const dy = user.y - p.y;
        const dSq = dx * dx + dy * dy;
        if (dSq > connSq) continue;
        const dist = Math.sqrt(dSq);
        const s = 1 - dist / connDist;
        const lineAlpha = focused ? s * 0.12 : (p.recognizedAt > 0 && now - p.recognizedAt < 2500)
          ? s * (0.6 - (now - p.recognizedAt) / 2500 * 0.35)
          : s * 0.2;
        const lineWidth = focused ? 0.5 : (p.recognizedAt > 0 && now - p.recognizedAt < 2500)
          ? 1.4 - (now - p.recognizedAt) / 2500 * 0.6
          : 0.7;
        const [cr, cg, cb] = p.color;
        const bl = 0.3;
        ctx!.strokeStyle = `rgba(${cr + (255 - cr) * bl | 0},${cg + (255 - cg) * bl | 0},${cb + (255 - cb) * bl | 0},${lineAlpha})`;
        ctx!.lineWidth = lineWidth;
        ctx!.beginPath();
        ctx!.moveTo(user.x, user.y);
        ctx!.lineTo(p.x, p.y);
        ctx!.stroke();
      }

      // Pulses
      for (let i = pulses.length - 1; i >= 0; i--) {
        const pulse = pulses[i];
        const prog = (now - pulse.startTime) / PULSE_DURATION;
        if (prog < 0) continue;
        if (prog >= 1) { pulses.splice(i, 1); continue; }
        const [cr, cg, cb] = pulse.color;
        ctx!.strokeStyle = `rgba(${cr},${cg},${cb},${0.5 * (1 - prog) ** 2})`;
        ctx!.lineWidth = 1.8 * (1 - prog * 0.6);
        ctx!.beginPath();
        ctx!.arc(pulse.x, pulse.y, 3 + 55 * prog, 0, Math.PI * 2);
        ctx!.stroke();
      }

      // Draw other particles
      for (const p of particles) {
        if (p.isUser) continue;
        const [r, g, b] = p.color;
        const bl = p.recognized ? 0.35 : 0;
        const dr = r + (255 - r) * bl | 0;
        const dg = g + (255 - g) * bl | 0;
        const db = b + (255 - b) * bl | 0;

        if (p.recognized && p.alpha > 0.3) {
          ctx!.fillStyle = `rgba(${dr},${dg},${db},${(p.alpha - 0.3) * 0.07})`;
          ctx!.beginPath();
          ctx!.arc(p.x, p.y, p.radius * 10, 0, Math.PI * 2);
          ctx!.fill();
          ctx!.fillStyle = `rgba(${dr},${dg},${db},${(p.alpha - 0.3) * 0.18})`;
          ctx!.beginPath();
          ctx!.arc(p.x, p.y, p.radius * 3.5, 0, Math.PI * 2);
          ctx!.fill();
        }
        ctx!.fillStyle = `rgba(${dr},${dg},${db},${p.alpha})`;
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx!.fill();
      }

      // Draw user particle (full mode only)
      if (!focused && !ambient) {
        const userPulse = 0.5 + 0.5 * Math.sin(now * 0.003);
        const ringRadius = 8 + userPulse * 3;

        ctx!.fillStyle = `rgba(255, 255, 255, ${0.03 + userPulse * 0.02})`;
        ctx!.beginPath();
        ctx!.arc(user.x, user.y, 22, 0, Math.PI * 2);
        ctx!.fill();

        ctx!.fillStyle = `rgba(255, 255, 255, ${0.08 + userPulse * 0.04})`;
        ctx!.beginPath();
        ctx!.arc(user.x, user.y, 10, 0, Math.PI * 2);
        ctx!.fill();

        ctx!.strokeStyle = `rgba(255, 255, 255, ${0.15 + userPulse * 0.1})`;
        ctx!.lineWidth = 0.8;
        ctx!.beginPath();
        ctx!.arc(user.x, user.y, ringRadius, 0, Math.PI * 2);
        ctx!.stroke();

        ctx!.fillStyle = "rgba(255, 255, 255, 0.95)";
        ctx!.beginPath();
        ctx!.arc(user.x, user.y, user.radius, 0, Math.PI * 2);
        ctx!.fill();

        // "You" label
        ctx!.save();
        ctx!.font = "600 9px system-ui, -apple-system, sans-serif";
        ctx!.letterSpacing = "2px";
        ctx!.fillStyle = "rgba(255,255,255,0.28)";
        ctx!.fillText("YOU", user.x + 11, user.y - 10);
        ctx!.restore();
      }

      // Labels (full + focused only)
      if (!ambient) ctx!.font = "500 10.5px system-ui, -apple-system, sans-serif";
      for (let i = labels.length - 1; !ambient && i >= 0; i--) {
        const lbl = labels[i];
        const elapsed = now - lbl.startTime;
        if (elapsed < 0) continue;
        if (elapsed > LABEL_DURATION) { labels.splice(i, 1); continue; }
        const prog = elapsed / LABEL_DURATION;
        let la = prog < 0.05 ? prog / 0.05 : prog > 0.7 ? (1 - prog) / 0.3 : 1;
        la *= 0.8;
        ctx!.fillStyle = `rgba(255,255,255,${la})`;
        ctx!.fillText(lbl.text, lbl.x + 8, lbl.y - 6 - elapsed * 0.005);
      }

      // Persistent tags
      ctx!.font = "400 8.5px system-ui, -apple-system, sans-serif";
      for (let i = tags.length - 1; i >= 0; i--) {
        const tag = tags[i];
        if (!tag.particle.recognized) { tags.splice(i, 1); continue; }
        const age = now - tag.createdAt;
        if (age < LABEL_DURATION) continue;
        const fadeIn = Math.min(1, (age - LABEL_DURATION) / 800);
        ctx!.fillStyle = `rgba(255,255,255,${fadeIn * (focused ? 0.30 : ambient ? 0.32 : 0.25)})`;
        ctx!.fillText(tag.text, tag.particle.x + 6, tag.particle.y - 5);
      }

      // Vignette
      const vigCY = focused ? height * 0.42 : height * 0.45;
      const vig = ctx!.createRadialGradient(
        centerX, vigCY, Math.min(width, height) * (focused ? 0.25 : 0.4),
        centerX, vigCY, Math.max(width, height) * (focused ? 0.6 : 0.85),
      );
      vig.addColorStop(0, "rgba(0,0,0,0)");
      vig.addColorStop(0.5, `rgba(0,0,0,${focused ? 0.1 : 0.05})`);
      vig.addColorStop(1, `rgba(0,0,0,${focused ? 0.5 : 0.30})`);
      ctx!.fillStyle = vig;
      ctx!.fillRect(0, 0, width, height);

      // Viewfinder + HUD (full mode only)
      if (!focused && !ambient) {
        const vfW = Math.min(width * 0.82, 340);
        const vfH = vfW * (10 / 17);
        const vfX = (width - vfW) / 2;
        const vfY = centerY - vfH * 0.45;

        const L = 16;
        ctx!.strokeStyle = "rgba(255,255,255,0.13)";
        ctx!.lineWidth = 1;
        ctx!.lineJoin = "miter";
        ctx!.beginPath();
        ctx!.moveTo(vfX, vfY + L); ctx!.lineTo(vfX, vfY); ctx!.lineTo(vfX + L, vfY);
        ctx!.moveTo(vfX + vfW, vfY + L); ctx!.lineTo(vfX + vfW, vfY); ctx!.lineTo(vfX + vfW - L, vfY);
        ctx!.moveTo(vfX, vfY + vfH - L); ctx!.lineTo(vfX, vfY + vfH); ctx!.lineTo(vfX + L, vfY + vfH);
        ctx!.moveTo(vfX + vfW, vfY + vfH - L); ctx!.lineTo(vfX + vfW, vfY + vfH); ctx!.lineTo(vfX + vfW - L, vfY + vfH);
        ctx!.stroke();

        let recCount = 0;
        for (const p of particles) if (p.recognized && !p.isUser) recCount++;

        ctx!.font = "600 10px system-ui, -apple-system, sans-serif";
        ctx!.letterSpacing = "0.6px";
        const hudY = vfY + vfH - 6;
        ctx!.fillStyle = "rgba(145, 65, 255, 0.75)";
        ctx!.fillText(`${recCount} identified`, vfX + 6, hudY);

        const blinkOn = Math.sin(now * 0.004) > 0;
        if (blinkOn) {
          ctx!.fillStyle = "rgba(100, 220, 160, 0.9)";
          ctx!.beginPath();
          ctx!.arc(vfX + vfW - 8, hudY - 3, 2.5, 0, Math.PI * 2);
          ctx!.fill();
        }
        ctx!.fillStyle = "rgba(255,255,255,0.45)";
        ctx!.fillText("scanning", vfX + vfW - 60, hudY);
        ctx!.letterSpacing = "0px";
      }
    }

    rafRef.current = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", resize);
    };
  }, [mode]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none ${className}`}
      style={{ width: "100%", height: "100%" }}
      aria-hidden="true"
    />
  );
}
