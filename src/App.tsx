import { useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { Home } from './sections/Home';
import { ChiSiamo, Servizi, Contatti, Approfondimenti, DoveCiTroviamo } from './sections/Contenuti';
import { Ricerca } from './sections/Ricerca';
import { Orari } from './sections/Orari';
import { SmoothScrollProvider } from './lib/smoothScroll';
import { prefersReducedMotion } from './lib/motion';

gsap.registerPlugin(ScrollTrigger, useGSAP);

export default function App() {
  const main = useRef<HTMLElement>(null);

  // Comparsa morbida dei contenuti allo scroll.
  useGSAP(
    () => {
      if (prefersReducedMotion()) return;
      ScrollTrigger.batch('[data-reveal]', {
        start: 'top 88%',
        once: true,
        onEnter: (els) =>
          gsap.fromTo(els, { y: 36, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 1.1, ease: 'power3.out', stagger: 0.08 }),
      });
    },
    { scope: main },
  );

  return (
    <SmoothScrollProvider>
      <a className="skip-link" href="#chi-siamo">
        Vai ai contenuti
      </a>
      <Header />
      <main ref={main}>
        <Home />
        <ChiSiamo />
        <Servizi />
        <Ricerca />
        <Contatti />
        <Orari />
        <Approfondimenti />
        <DoveCiTroviamo />
      </main>
      <Footer />
    </SmoothScrollProvider>
  );
}
