import { CONTATTI, INDIRIZZO_COMPLETO, MAPS_URL } from '../data/site';
import { LogoMark, Wordmark } from './Logo';

const ANNO = new Date().getFullYear();

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container site-footer__inner">
        <div className="site-footer__brand">
          <LogoMark className="site-footer__mark" />
          <Wordmark />
        </div>
        <div className="site-footer__cols">
          <a href={MAPS_URL} target="_blank" rel="noopener noreferrer">
            {INDIRIZZO_COMPLETO}
          </a>
          <a href={CONTATTI.telefonoHref}>Chiama {CONTATTI.telefonoVisibile}</a>
          <a href={CONTATTI.emailHref}>{CONTATTI.email}</a>
        </div>
      </div>
      <div className="container site-footer__legal">
        <p>© {ANNO} Domus Re Immobiliare</p>
        <p>Le scene 3D della home sono ricostruzioni dimostrative: l’appartamento mostrato è immaginario e non è un immobile in vendita.</p>
      </div>
    </footer>
  );
}
