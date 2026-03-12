(function () {
  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function clamp(n, a, b) {
    return Math.max(a, Math.min(b, n));
  }

  function startParticles(canvas, options = {}) {
    if (!canvas) return () => {};
    if (prefersReducedMotion()) return () => {};

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return () => {};

    const palette = options.palette || [
      "rgba(16,185,129,0.9)",
      "rgba(56,189,248,0.9)",
      "rgba(168,85,247,0.9)",
      "rgba(245,158,11,0.9)",
    ];

    let raf = 0;
    let width = 0;
    let height = 0;
    let dpr = 1;
    let particles = [];

    function resize() {
      dpr = clamp(window.devicePixelRatio || 1, 1, 2);
      width = Math.max(1, window.innerWidth);
      height = Math.max(1, window.innerHeight);

      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const target = clamp(Math.floor((width * height) / 18000), 28, 90);
      particles = Array.from({ length: target }, () => makeParticle());
    }

    function makeParticle() {
      const r = Math.random() * 2.1 + 0.7;
      const speed = Math.random() * 0.35 + 0.12;
      const angle = Math.random() * Math.PI * 2;
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        r,
        a: Math.random() * 0.35 + 0.15,
        c: palette[Math.floor(Math.random() * palette.length)],
      };
    }

    function drawGlow(p) {
      const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 9);
      g.addColorStop(0, p.c.replace("0.9", String(p.a)));
      g.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 9, 0, Math.PI * 2);
      ctx.fill();
    }

    function frame() {
      ctx.clearRect(0, 0, width, height);

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < -20) p.x = width + 20;
        if (p.x > width + 20) p.x = -20;
        if (p.y < -20) p.y = height + 20;
        if (p.y > height + 20) p.y = -20;

        drawGlow(p);
      }

      // links
      const maxDist = 120;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i];
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 > maxDist * maxDist) continue;
          const t = 1 - Math.sqrt(d2) / maxDist;
          ctx.strokeStyle = `rgba(15, 23, 42, ${0.08 * t})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      raf = window.requestAnimationFrame(frame);
    }

    const onResize = () => resize();
    window.addEventListener("resize", onResize, { passive: true });
    resize();
    raf = window.requestAnimationFrame(frame);

    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }

  window.startParticles = startParticles;
})();

