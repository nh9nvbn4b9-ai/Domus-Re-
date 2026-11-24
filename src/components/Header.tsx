import { useEffect, useId, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { useGSAP } from '@gsap/react';
import { SEZIONI, CONTATTI } from '../data/site';
import { useScrollTo } from '../lib/scrollContext';
import { prefersReducedMotion } from '../lib/motion';
import { LogoMark, Wordmark } from './Logo';

export function Header() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const scrollTo = useScrollTo();
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    const onClick = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!panelRef.current?.contains(t) && !buttonRef.current?.contains(t)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClick);
    };
  }, [open]);

  useGSAP(
    () => {
      const panel = panelRef.current;
      if (!panel) return;
      const items = panel.querySelectorAll('.menu__item');
      const d = prefersReducedMotion() ? 0 : 1;
      if (open) {
        gsap.set(panel, { visibility: 'visible' });
        gsap.fromTo(panel, { clipPath: 'inset(0 0 100% 0)' }, { clipPath: 'inset(0 0 0% 0)', duration: 0.7 * d, ease: 'expo.out' });
        gsap.fromTo(items, { y: 24, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.6 * d, stagger: 0.045 * d, ease: 'power3.out', delay: 0.12 * d });
      } else {
        gsap.to(panel, {
          clipPath: 'inset(0 0 100% 0)',
          duration: 0.45 * d,
          ease: 'power3.inOut',
          onComplete: () => gsap.set(panel, { visibility: 'hidden' }),
        });
      }
    },
    { dependencies: [open] },
  );

  const vai = (id: string) => {
    setOpen(false);
    scrollTo(id);
  };

  return (
    <header className={`site-header ${scrolled || open ? 'is-solid' : ''}`}>
      <div className="site-header__bar">
        <a
          href="#home"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            vai('home');
          }}
        >
          <LogoMark className="brand__mark" />
          <Wordmark compact />
        </a>

        <div className="site-header__actions">
          <a className="pill pill--ghost hide-sm" href={CONTATTI.telefonoHref}>
            Chiama
          </a>
          <button
            ref={buttonRef}
            type="button"
            className={`menu-toggle ${open ? 'is-open' : ''}`}
            aria-expanded={open}
            aria-controls={menuId}
            onClick={() => setOpen((v) => !v)}
          >
            <span className="menu-toggle__label">{open ? 'Chiudi' : 'Menu'}</span>
            <span className="menu-toggle__icon" aria-hidden="true">
              <span />
              <span />
            </span>
          </button>
        </div>
      </div>

      <div ref={panelRef} id={menuId} className="menu" style={{ visibility: 'hidden' }}>
        <nav aria-label="Sezioni del sito">
          <ol className="menu__list">
            {SEZIONI.map((s, i) => (
              <li key={s.id} className="menu__item">
                <a
                  href={`#${s.id}`}
                  onClick={(e) => {
                    e.preventDefault();
                    vai(s.id);
                  }}
                >
                  <span className="menu__num">{String(i + 1).padStart(2, '0')}</span>
                  <span className="menu__label">{s.label}</span>
                </a>
              </li>
            ))}
          </ol>
        </nav>
      </div>
    </header>
  );
}
