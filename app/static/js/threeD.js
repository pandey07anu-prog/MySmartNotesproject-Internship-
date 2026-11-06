/**
 * Smart Notes Assistant — Interactive 3D Engine & Parallax System
 * 1. Apple-Style 3D Perspective Card Tilt & Specular Glare
 * 2. Ambient 3D Interactive Background Starfield
 * 3. "3D Thought Cosmos" — Interactive 360° Orbiting Neural Galaxy of Notes
 */

const ThreeD = {
  // ---------------------------------------------------------------------------
  // 1. APPLE-STYLE 3D PREVIEW PERSPECTIVE TILT
  // ---------------------------------------------------------------------------
  hero3DAnimId: null,
  heroTargetRotX: 0,
  heroTargetRotY: 0,
  heroCurrentRotX: 0,
  heroCurrentRotY: 0,
  heroMouseX: 0,
  heroMouseY: 0,

  initHero3DStage() {
    const card = document.getElementById('main-preview-card');
    if (!card) return;

    if (this.hero3DAnimId) {
      cancelAnimationFrame(this.hero3DAnimId);
      this.hero3DAnimId = null;
    }

    const onMove = (e) => {
      const rect = card.getBoundingClientRect();
      // Check if mouse is near or over the card
      if (
        e.clientX >= rect.left - 40 &&
        e.clientX <= rect.right + 40 &&
        e.clientY >= rect.top - 40 &&
        e.clientY <= rect.bottom + 40
      ) {
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        // Subtle, luxurious Apple TV-grade 3D tilt (max 3.5 degrees)
        const normX = (e.clientX - centerX) / (rect.width / 2);
        const normY = (e.clientY - centerY) / (rect.height / 2);

        this.heroTargetRotX = Math.max(-3.5, Math.min(3.5, -normY * 3.5));
        this.heroTargetRotY = Math.max(-4.5, Math.min(4.5, normX * 4.5));
        this.heroMouseX = e.clientX - rect.left;
        this.heroMouseY = e.clientY - rect.top;
      } else {
        // Return to completely flat, crisp state
        this.heroTargetRotX = 0;
        this.heroTargetRotY = 0;
      }
    };

    window.addEventListener('mousemove', onMove);

    window.addEventListener('mouseleave', () => {
      this.heroTargetRotX = 0;
      this.heroTargetRotY = 0;
    });

    const loop = () => {
      this.heroCurrentRotX += (this.heroTargetRotX - this.heroCurrentRotX) * 0.1;
      this.heroCurrentRotY += (this.heroTargetRotY - this.heroCurrentRotY) * 0.1;

      card.style.transform = `perspective(1000px) rotateX(${this.heroCurrentRotX.toFixed(2)}deg) rotateY(${this.heroCurrentRotY.toFixed(2)}deg)`;

      // Specular glare inside card
      const glare = card.querySelector('.specular-3d-glare');
      if (glare) {
        if (Math.abs(this.heroCurrentRotX) > 0.05 || Math.abs(this.heroCurrentRotY) > 0.05) {
          const rect = card.getBoundingClientRect();
          const gx = ((this.heroMouseX) / (rect.width || 1)) * 100;
          const gy = ((this.heroMouseY) / (rect.height || 1)) * 100;
          glare.style.background = `radial-gradient(circle at ${gx}% ${gy}%, rgba(255, 255, 255, 0.4) 0%, transparent 60%)`;
          glare.style.opacity = '1';
        } else {
          glare.style.opacity = '0';
        }
      }

      this.hero3DAnimId = requestAnimationFrame(loop);
    };

    loop();
  },

  // ---------------------------------------------------------------------------
  // 2. GENERAL CARD PARALLAX TILT
  // ---------------------------------------------------------------------------
  initParallax3D() {
    const cardSelectors = [
      '.roomy-activity-card',
      '.roomy-stat-card',
      '.ai-digest-banner',
      '.sticky-note-card',
      '.note-card',
      '.library-kpi-card',
      '.quad-tile',
      '.hero-feature-card',
      '.roomy-progress-card'
    ];

    document.addEventListener('mousemove', (e) => {
      const cards = document.querySelectorAll(cardSelectors.join(','));
      cards.forEach(card => {
        const rect = card.getBoundingClientRect();
        if (
          e.clientX >= rect.left - 15 &&
          e.clientX <= rect.right + 15 &&
          e.clientY >= rect.top - 15 &&
          e.clientY <= rect.bottom + 15
        ) {
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;
          const centerX = rect.width / 2;
          const centerY = rect.height / 2;

          const rotateX = ((y - centerY) / centerY) * -5;
          const rotateY = ((x - centerX) / centerX) * 5;

          card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateZ(6px)`;
          card.style.transition = 'transform 0.1s ease-out';
        } else if (card.style.transform && card.style.transform.includes('perspective')) {
          card.style.transform = '';
          card.style.transition = 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
        }
      });
    });
  },

  // ---------------------------------------------------------------------------
  // 3. AMBIENT 3D BACKGROUND PARTICLE CONSTELLATION
  // ---------------------------------------------------------------------------
  constellationAnimId: null,
  initBackgroundConstellation() {
    const canvas = document.getElementById('interactive-3d-bg');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    window.addEventListener('resize', () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });

    const particles = [];
    const count = Math.min(40, Math.floor(width / 36));
    const colors = ['rgba(108, 82, 238, 0.35)', 'rgba(56, 189, 248, 0.3)', 'rgba(139, 92, 246, 0.3)', 'rgba(52, 211, 153, 0.25)'];

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        z: Math.random() * 300 - 150,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        vz: (Math.random() - 0.5) * 0.2,
        radius: Math.random() * 1.8 + 1,
        color: colors[i % colors.length]
      });
    }

    let mouseX = width / 2;
    let mouseY = height / 2;

    window.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    });

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Connect nearby particles in 3D
      for (let i = 0; i < particles.length; i++) {
        const p1 = particles[i];
        p1.x += p1.vx;
        p1.y += p1.vy;
        p1.z += p1.vz;

        if (p1.x < 0) p1.x = width;
        if (p1.x > width) p1.x = 0;
        if (p1.y < 0) p1.y = height;
        if (p1.y > height) p1.y = 0;
        if (p1.z < -150 || p1.z > 150) p1.vz *= -1;

        // Subtle mouse attraction
        const dx = mouseX - p1.x;
        const dy = mouseY - p1.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 150) {
          p1.x += (dx / dist) * 0.25;
          p1.y += (dy / dist) * 0.25;
        }

        // Draw connections
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dist3d = Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2);
          if (dist3d < 100) {
            const alpha = (1 - dist3d / 100) * 0.12;
            ctx.strokeStyle = `rgba(108, 82, 238, ${alpha})`;
            ctx.lineWidth = 0.7;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }

        // Draw particle node with 3D depth scaling
        const scale = (p1.z + 250) / 350;
        ctx.fillStyle = p1.color;
        ctx.beginPath();
        ctx.arc(p1.x, p1.y, Math.max(0.7, p1.radius * scale), 0, Math.PI * 2);
        ctx.fill();
      }

      this.constellationAnimId = requestAnimationFrame(render);
    };

    render();
  },
      for (let i = 0; i < particles.length; i++) {
        const p1 = particles[i];
        p1.x += p1.vx;
        p1.y += p1.vy;
        p1.z += p1.vz;

        if (p1.x < 0) p1.x = width;
        if (p1.x > width) p1.x = 0;
        if (p1.y < 0) p1.y = height;
        if (p1.y > height) p1.y = 0;
        if (p1.z < -200 || p1.z > 200) p1.vz *= -1;

        // Subtle mouse attraction
        const dx = mouseX - p1.x;
        const dy = mouseY - p1.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 180) {
          p1.x += (dx / dist) * 0.3;
          p1.y += (dy / dist) * 0.3;
        }

        // Draw connections
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dist3d = Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2);
          if (dist3d < 110) {
            const alpha = (1 - dist3d / 110) * 0.15;
            ctx.strokeStyle = `rgba(140, 120, 234, ${alpha})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }

        // Draw particle node with 3D depth scaling
        const scale = (p1.z + 300) / 400;
        ctx.fillStyle = p1.color;
        ctx.beginPath();
        ctx.arc(p1.x, p1.y, Math.max(0.8, p1.radius * scale), 0, Math.PI * 2);
        ctx.fill();
      }

      this.constellationAnimId = requestAnimationFrame(render);
    };

    render();
  },

  // ---------------------------------------------------------------------------
  // 3. "3D THOUGHT COSMOS" (Interactive 360° Rotating Neural Galaxy)
  // ---------------------------------------------------------------------------
  cosmosCanvas: null,
  cosmosCtx: null,
  cosmosAnimId: null,
  rotX: 0.2,
  rotY: 0.3,
  targetRotX: 0.2,
  targetRotY: 0.3,
  zoom: 1,
  isDragging: false,
  lastMouseX: 0,
  lastMouseY: 0,
  hoveredNode: null,

  openCosmosModal() {
    const modal = document.getElementById('cosmos-modal');
    const canvas = document.getElementById('cosmos-canvas');
    if (!modal || !canvas) return;

    modal.classList.add('active');
    this.cosmosCanvas = canvas;
    this.cosmosCtx = canvas.getContext('2d');

    // Give browser a frame to layout modal
    requestAnimationFrame(() => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = (rect.width || 800) * dpr;
      canvas.height = (rect.height || 500) * dpr;
      this.cosmosCtx.scale(dpr, dpr);

      this.bindCosmosEvents(canvas);
      this.startCosmosLoop();
    });

    if (window.App && App.showToast) {
      App.showToast('🌌 3D Thought Galaxy active — Click & drag to rotate in 360°!', 'info');
    }
  },

  closeCosmosModal() {
    const modal = document.getElementById('cosmos-modal');
    if (modal) modal.classList.remove('active');
    if (this.cosmosAnimId) {
      cancelAnimationFrame(this.cosmosAnimId);
      this.cosmosAnimId = null;
    }
  },

  bindCosmosEvents(canvas) {
    canvas.onmousedown = (e) => {
      this.isDragging = true;
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
    };

    window.onmousemove = (e) => {
      if (this.isDragging) {
        const dx = e.clientX - this.lastMouseX;
        const dy = e.clientY - this.lastMouseY;
        this.targetRotY += dx * 0.008;
        this.targetRotX += dy * 0.008;
        this.lastMouseX = e.clientX;
        this.lastMouseY = e.clientY;
      }
    };

    window.onmouseup = () => {
      this.isDragging = false;
    };

    canvas.onwheel = (e) => {
      e.preventDefault();
      this.zoom += e.deltaY * -0.001;
      this.zoom = Math.max(0.6, Math.min(2.0, this.zoom));
    };

    // Touch support for mobile devices
    canvas.ontouchstart = (e) => {
      if (e.touches.length === 1) {
        this.isDragging = true;
        this.lastMouseX = e.touches[0].clientX;
        this.lastMouseY = e.touches[0].clientY;
      }
    };

    canvas.ontouchmove = (e) => {
      if (this.isDragging && e.touches.length === 1) {
        const dx = e.touches[0].clientX - this.lastMouseX;
        const dy = e.touches[0].clientY - this.lastMouseY;
        this.targetRotY += dx * 0.008;
        this.targetRotX += dy * 0.008;
        this.lastMouseX = e.touches[0].clientX;
        this.lastMouseY = e.touches[0].clientY;
      }
    };

    canvas.ontouchend = () => {
      this.isDragging = false;
    };
  },

  startCosmosLoop() {
    const canvas = this.cosmosCanvas;
    const ctx = this.cosmosCtx;
    if (!canvas || !ctx) return;

    const userNotes = App.notes || [];
    const notes = userNotes.length > 0 ? userNotes : [
      { note_id: 'demo-1', text: 'Welcome to Smart Notes', category: 'Study' },
      { note_id: 'demo-2', text: 'Intelligent ML Classifier', category: 'Study' },
      { note_id: 'demo-3', text: 'Financial Budget & Savings', category: 'Money' },
      { note_id: 'demo-4', text: 'Trip to Himachal Pradesh', category: 'Travel' },
      { note_id: 'demo-5', text: 'Organic groceries & supplies', category: 'Shopping' },
      { note_id: 'demo-6', text: 'Weekend getaway plans', category: 'Travel' }
    ];
    const w = canvas.getBoundingClientRect().width;
    const h = canvas.getBoundingClientRect().height;
    const centerX = w / 2;
    const centerY = h / 2;

    // Generate 3D sphere coordinates for each note
    const nodes = notes.map((n, i) => {
      const phi = Math.acos(-1 + (2 * i) / Math.max(1, notes.length));
      const theta = Math.sqrt(notes.length * Math.PI) * phi;
      const radius = 180;
      return {
        id: n.note_id,
        text: n.text,
        category: n.category || 'Study',
        x: radius * Math.cos(theta) * Math.sin(phi),
        y: radius * Math.sin(theta) * Math.sin(phi),
        z: radius * Math.cos(phi),
        color: n.category === 'Study' ? '#3B82F6' : n.category === 'Money' ? '#10B981' : n.category === 'Travel' ? '#F59E0B' : '#EC4899'
      };
    });

    const loop = () => {
      ctx.clearRect(0, 0, w, h);

      // Smooth camera interpolation
      this.rotX += (this.targetRotX - this.rotX) * 0.08;
      this.rotY += (this.targetRotY - this.rotY) * 0.08;

      // Auto gentle rotation if not dragging
      if (!this.isDragging) {
        this.targetRotY += 0.002;
      }

      const cosY = Math.cos(this.rotY);
      const sinY = Math.sin(this.rotY);
      const cosX = Math.cos(this.rotX);
      const sinX = Math.sin(this.rotX);

      // Project 3D points to 2D
      const projected = nodes.map(node => {
        // Rotate Y
        let x1 = node.x * cosY - node.z * sinY;
        let z1 = node.z * cosY + node.x * sinY;

        // Rotate X
        let y1 = node.y * cosX - z1 * sinX;
        let z2 = z1 * cosX + node.y * sinX;

        // Perspective projection
        const fov = 400 * this.zoom;
        const scale = fov / (fov + z2);
        const px = x1 * scale + centerX;
        const py = y1 * scale + centerY;

        return { ...node, px, py, pz: z2, scale };
      });

      // Sort by depth (painter's algorithm)
      projected.sort((a, b) => b.pz - a.pz);

      // Draw 3D Neural connecting lines between same-category notes
      for (let i = 0; i < projected.length; i++) {
        for (let j = i + 1; j < projected.length; j++) {
          const n1 = projected[i];
          const n2 = projected[j];
          if (n1.category === n2.category) {
            ctx.beginPath();
            ctx.moveTo(n1.px, n1.py);
            ctx.lineTo(n2.px, n2.py);
            ctx.strokeStyle = n1.color;
            ctx.globalAlpha = Math.min(0.28, Math.max(0.04, (n1.scale + n2.scale) * 0.1));
            ctx.lineWidth = 1.2 * this.zoom;
            ctx.stroke();
          }
        }
      }

      ctx.globalAlpha = 1.0;

      // Draw 3D Nodes
      projected.forEach(node => {
        const radius = Math.max(4, 9 * node.scale);

        // Glow halo
        const grad = ctx.createRadialGradient(node.px, node.py, 1, node.px, node.py, radius * 2.2);
        grad.addColorStop(0, node.color);
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(node.px, node.py, radius * 2.2, 0, Math.PI * 2);
        ctx.fill();

        // Solid core
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(node.px, node.py, radius * 0.65, 0, Math.PI * 2);
        ctx.fill();

        // Node Label
        if (node.scale > 0.7) {
          ctx.font = `${Math.round(11 * node.scale)}px -apple-system, BlinkMacSystemFont, sans-serif`;
          ctx.fillStyle = node.color;
          ctx.textAlign = 'center';
          const label = node.text.length > 20 ? node.text.substring(0, 20) + '...' : node.text;
          ctx.fillText(label, node.px, node.py + radius + 12);
        }
      });

      this.cosmosAnimId = requestAnimationFrame(loop);
    };

    loop();
  }
};

// Auto-initialize when script loads
document.addEventListener('DOMContentLoaded', () => {
  ThreeD.initHero3DStage();
  ThreeD.initParallax3D();
  ThreeD.initBackgroundConstellation();
});
