# Design System — Baseflow Inspired

Design system dark, moderno e minimalista extraído visualmente de baseflow.webflow.io. Pronto para uso em produtos SaaS com IA.

---

## Direção Visual

**Estilo:** Dark UI · Tech-futurista · AI SaaS premium  
**Paleta:** Fundo preto absoluto + azul elétrico como único acento  
**Efeitos:** Glow radial azul no hero e seções de destaque; glassmorphism leve em cards  
**Tipografia:** Plus Jakarta Sans — moderna, geométrica, com headings extrabold  
**Sensação:** Confiante, poderoso, clean. Feito para times técnicos e product-led growth

---

## Estrutura de arquivos

```
src/
  tokens.css              ← Variáveis CSS (fonte da verdade)
  tokens.json             ← Tokens em JSON (Figma/Tailwind/JS)
  components/
    buttons.css           ← primary, secondary, ghost, danger + sm/md/lg
    navbar.css            ← Sticky nav com blur + mobile hamburger
    hero.css              ← Hero section + dashboard mockup
    cards.css             ← KPI, Feature, Step, Testimonial, Pricing, FAQ
    charts.css            ← Area chart, sparkline, bar chart (SVG nativo)
    forms.css             ← Input, select, checkbox, toggle, input-group
    misc.css              ← Badge, chip, avatar, tabs, tooltip, modal, carousel, marquee
index.html                ← Showcase completo (todos os componentes)
_research/
  analysis.md             ← Análise visual detalhada
  screenshots/            ← Capturas desktop + mobile do site original
```

---

## Paleta de cores

| Token CSS | Valor | Uso |
|-----------|-------|-----|
| `--color-bg` | `#000000` | Fundo da página |
| `--color-surface-1` | `#111116` | Cards, sidebar |
| `--color-surface-2` | `#1a1a24` | Cards principais |
| `--color-surface-3` | `#22222e` | FAQ, hover states |
| `--color-primary` | `#3B72FF` | Botões, links, ícones |
| `--color-primary-light` | `#5B9AFF` | Hover, badges |
| `--color-success` | `#22C55E` | Checkmarks, KPI positivo |
| `--color-danger` | `#EF4444` | Erros, KPI negativo |
| `--color-text-primary` | `#FFFFFF` | Headings |
| `--color-text-secondary` | `#9CA3AF` | Body text |
| `--color-border` | `rgba(255,255,255,0.08)` | Bordas sutis |

### Gradientes chave

```css
/* Spotlight do hero */
background: radial-gradient(ellipse 70% 60% at 50% -10%, rgba(59,114,255,0.40) 0%, transparent 70%);

/* Botão primário */
background: linear-gradient(90deg, #3B72FF 0%, #5B9AFF 100%);

/* Texto grande (rodapé) */
background: linear-gradient(180deg, #ffffff 0%, #3B72FF 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
```

---

## Tipografia

**Fonte:** Plus Jakarta Sans

```html
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
```

| Token | Tamanho | Peso | Uso |
|-------|---------|------|-----|
| `--text-hero` | 72px (clamp) | 800 | H1 hero |
| `--text-h1` | 56px (clamp) | 700 | Títulos de seção |
| `--text-h2` | 40px (clamp) | 700 | Sub-títulos |
| `--text-h3` | 24px | 600 | Card titles |
| `--text-base` | 16px | 400 | Body |
| `--text-sm` | 14px | 400 | Labels, hints |
| `--text-xs` | 12px | 500 | Badges, captions |

---

## Uso dos componentes

### Importação

```html
<link rel="stylesheet" href="src/tokens.css">
<link rel="stylesheet" href="src/components/buttons.css">
<!-- adicione os demais conforme necessário -->
```

### Botões

```html
<button class="btn btn--primary btn--lg">Try for free <span class="btn-arrow">→</span></button>
<button class="btn btn--secondary">Book a Demo</button>
<button class="btn btn--ghost">Saiba mais</button>
<button class="btn btn--primary" disabled>Desabilitado</button>
```

### KPI Card

```html
<div class="card-kpi">
  <div class="card-kpi__label">Total Revenue</div>
  <div class="card-kpi__value">
    $50.8k
    <span class="card-kpi__badge card-kpi__badge--up">↑ 12.5%</span>
  </div>
</div>
```

### Pricing Card (destaque)

```html
<div class="card-pricing card-pricing--featured">
  <div class="card-pricing__name">Business Plan</div>
  <div class="card-pricing__price">$29<span>/month</span></div>
  <button class="btn btn--primary" style="width:100%">Get Started →</button>
</div>
```

### FAQ Accordion

```html
<div class="card-faq" id="faq1">
  <div class="card-faq__question" onclick="toggleFaq('faq1')">
    Pergunta?
    <svg class="card-faq__icon"><!-- + --></svg>
  </div>
  <div class="card-faq__answer">
    <div class="card-faq__answer-inner">Resposta.</div>
  </div>
</div>
<script>
function toggleFaq(id) { document.getElementById(id).classList.toggle('is-open'); }
</script>
```

### Input Group (newsletter)

```html
<div class="input-group">
  <input class="input" type="email" placeholder="Enter your email">
  <button class="btn btn--primary btn--sm">Subscribe</button>
</div>
```

### Modal

```html
<div class="modal-overlay" id="modal"
     onclick="if(event.target===this)this.classList.remove('is-open')">
  <div class="modal">
    <div class="modal__header">
      <h3 class="modal__title">Título</h3>
      <button class="modal__close"
              onclick="document.getElementById('modal').classList.remove('is-open')">×</button>
    </div>
    <div class="modal__body">Conteúdo.</div>
    <div class="modal__footer">
      <button class="btn btn--ghost">Cancelar</button>
      <button class="btn btn--primary">Confirmar</button>
    </div>
  </div>
</div>
```

---

## Tokens em JS / Tailwind

```js
// Ler token em runtime
const primary = getComputedStyle(document.documentElement)
  .getPropertyValue('--color-primary').trim();

// tailwind.config.js
const tokens = require('./src/tokens.json');
module.exports = {
  theme: { extend: { colors: { primary: tokens.color.primary.DEFAULT } } }
};
```

---

## Rodar o showcase

```bash
python -m http.server 8787
# Acesse: http://localhost:8787
```
