import { useCallback, useEffect, useRef, type ReactNode } from 'react';
import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { prefersReducedMotion } from './motion';
import { ScrollContext, type ScrollToFn } from './scrollContext';

gsap.registerPlugin(ScrollTrigger);

/** Scroll fluido (Lenis) sincronizzato con il ticker di GSAP/ScrollTrigger. */
export function SmoothScrollProvider({ children }: { children: ReactNode }) {
  const lenisRef = useRef<Lenis | null>(null);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    const lenis = new Lenis({ autoRaf: false, lerp: 0.085, wheelMultiplier: 0.9 });
    lenisRef.current = lenis;
    lenis.on('scroll', ScrollTrigger.update);
    const tick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    return () => {
      gsap.ticker.remove(tick);
      lenis.destroy();
      lenisRef.current = null;
    };
  }, []);

  const scrollTo = useCallback<ScrollToFn>((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const offset = -(document.querySelector<HTMLElement>('.site-header')?.offsetHeight ?? 0);
    if (lenisRef.current) {
      lenisRef.current.scrollTo(id === 'home' ? 0 : el, { offset, duration: 1.6 });
    } else {
      el.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
    }
    history.replaceState(null, '', `#${id}`);
  }, []);

  return <ScrollContext.Provider value={scrollTo}>{children}</ScrollContext.Provider>;
}

