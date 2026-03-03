"use client";

import { useEffect, useRef } from "react";

const COLORS = [
  [145, 65, 255],
  [100, 70, 235],
  [65, 105, 225],
  [40, 165, 215],
] as const;

interface Particle {
  angle: number;
  orbitRadius: number;
  targetOrbit: number;
  speed: number;
  wobbleAmp: number;
  wobbleSpeed: number;
  wobblePhase: number;
  x: number;
  y: number;
  radius: number;
  color: readonly [number, number, number];
  alpha: number;
  bright: boolean;
}

const PARTICLE_COUNT = 30;
const CONNECTION_DIST = 110;
const BRIGHT_COUNT = 8;
const EXPAND_DURATION = 1800;

export function NetworkField({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let startTime = 0;

    function resize() {
      canvas!.width = Math.round(canvas!.clientWidth * dpr);
      canvas!.height = Math.round(canvas!.clientHeight * dpr);
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    const W = () => canvas!.clientWidth;
    const H = () => canvas!.clientHeight;

    const particles: Particle[] = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const angle = Math.random() * Math.PI * 2;
      const targetOrbit = 20 + Math.pow(Math.random(), 0.5) * 200;
      const color = COLORS[Math.floor(Math.random() * COLORS.length)];
      const bright = i < BRIGHT_COUNT;

      particles.push({
        angle,
        orbitRadius: targetOrbit * 0.15,
        targetOrbit,
        speed: (0.0001 + Math.random() * 0.0003) * (Math.random() < 0.5 ? 1 : -1),
        wobbleAmp: 4 + Math.random() * 14,
        wobbleSpeed: 0.15 + Math.random() * 0.3,
        wobblePhase: Math.random() * Math.PI * 2,
        x: 0,
        y: 0,
        radius: bright ? 2 : 0.8 + Math.random() * 0.6,
        color,
        alpha: bright ? 0.5 : 0.06 + Math.random() * 0.06,
        bright,
      });
    }

    let lastFrame = 0;

    function render(now: number) {
      rafRef.current = requestAnimationFrame(render);
      if (!startTime) startTime = now;
      if (now - lastFrame < 40) return;
      lastFrame = now;

      const width = W();
      const height = H();
      const centerX = width * 0.55;
      const centerY = height * 0.35;

      ctx!.clearRect(0, 0, width, height);

      const expandProg = Math.min(1, (now - startTime) / EXPAND_DURATION);
      const expandEase = 1 - Math.pow(1 - expandProg, 3);

      for (const p of particles) {
        p.orbitRadius += (p.targetOrbit - p.orbitRadius) * (0.01 + expandEase * 0.04);
        p.angle += p.speed * 33;
        const wx = Math.sin(now * 0.0006 * p.wobbleSpeed + p.wobblePhase) * p.wobbleAmp;
        const wy = Math.cos(now * 0.0005 * p.wobbleSpeed + p.wobblePhase + 1.5) * p.wobbleAmp * 0.6;
        p.x = centerX + Math.cos(p.angle) * p.orbitRadius + wx;
        p.y = centerY + Math.sin(p.angle) * p.orbitRadius * 0.6 + wy;
      }

      const cdSq = CONNECTION_DIST * CONNECTION_DIST;
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dSq = dx * dx + dy * dy;
          if (dSq > cdSq) continue;

          const dist = Math.sqrt(dSq);
          const s = 1 - dist / CONNECTION_DIST;
          const bothBright = a.bright && b.bright;
          const oneBright = a.bright || b.bright;

          const lineAlpha = bothBright ? s * 0.18 : oneBright ? s * s * 0.05 : s * s * 0.015;

          const br = a.alpha > b.alpha ? a : b;
          const [cr, cg, cb] = br.color;
          const bl = bothBright ? 0.25 : 0;

          ctx!.strokeStyle = `rgba(${cr + (255 - cr) * bl | 0},${cg + (255 - cg) * bl | 0},${cb + (255 - cb) * bl | 0},${lineAlpha * expandEase})`;
          ctx!.lineWidth = bothBright ? 0.8 : 0.4;
          ctx!.beginPath();
          ctx!.moveTo(a.x, a.y);
          ctx!.lineTo(b.x, b.y);
          ctx!.stroke();
        }
      }

      for (const p of particles) {
        const [r, g, b] = p.color;
        const bl = p.bright ? 0.25 : 0;
        const dr = r + (255 - r) * bl | 0;
        const dg = g + (255 - g) * bl | 0;
        const db = b + (255 - b) * bl | 0;

        if (p.bright) {
          ctx!.fillStyle = `rgba(${dr},${dg},${db},${p.alpha * 0.04 * expandEase})`;
          ctx!.beginPath();
          ctx!.arc(p.x, p.y, p.radius * 10, 0, Math.PI * 2);
          ctx!.fill();
        }

        ctx!.fillStyle = `rgba(${dr},${dg},${db},${p.alpha * expandEase})`;
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx!.fill();
      }

      const vig = ctx!.createRadialGradient(
        centerX, centerY, Math.min(width, height) * 0.15,
        centerX, centerY, Math.max(width, height) * 0.55,
      );
      vig.addColorStop(0, "rgba(0,0,0,0)");
      vig.addColorStop(1, "rgba(0,0,0,0.65)");
      ctx!.fillStyle = vig;
      ctx!.fillRect(0, 0, width, height);
    }

    rafRef.current = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none ${className}`}
      style={{ width: "100%", height: "100%" }}
      aria-hidden="true"
    />
  );
}
