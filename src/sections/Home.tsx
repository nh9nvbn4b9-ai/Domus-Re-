import { lazy, Suspense, useMemo } from 'react';
import { AGENZIA } from '../data/site';

const Experience = lazy(() => import('../three/Experience'));

function supportsWebGL2() {
  try {
    const c = document.createElement('canvas');
    return !!c.getContext('webgl2');
  } catch {
    return false;
  }
}

export function Home() {
  const webgl = useMemo(() => supportsWebGL2(), []);

  return (
    <section id="home" className="home" aria-label="Home">
      <div className="home__stage">
        {webgl ? (
          <Suspense fallback={<div className="home__loading" aria-hidden="true" />}>
            <Experience />
          </Suspense>
        ) : (
          // Solo per dispositivi senza WebGL: immagine di riferimento del palazzo.
          <img className="home__fallback" src="/images/palazzo-fallback.webp" alt="Facciata del palazzo" />
        )}
        <div className="home__vignette" aria-hidden="true" />
      </div>

      <div className="home__overlay">
        <p className="eyebrow">Agenzia immobiliare · {AGENZIA.citta}</p>
        <h1 className="visually-hidden">Domus Re Immobiliare</h1>
        <p className="home__scroll" aria-hidden="true">
          <span>Scorri</span>
          <span className="home__scroll-line" />
        </p>
      </div>
    </section>
  );
}
