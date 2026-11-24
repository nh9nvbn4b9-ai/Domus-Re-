import { lazy, Suspense, useState } from 'react';
import { CONTATTI, INDIRIZZO_COMPLETO, MAPS_DIREZIONI_URL, MAPS_URL, SERVIZI, AGENZIA } from '../data/site';

function SectionHead({ numero, titolo, id }: { numero: string; titolo: string; id: string }) {
  return (
    <header className="section-head" data-reveal>
      <span className="section-head__num">{numero}</span>
      <h2 id={`${id}-titolo`} className="section-head__title">
        {titolo}
      </h2>
    </header>
  );
}

export function ChiSiamo() {
  return (
    <section id="chi-siamo" className="section section--stone" aria-labelledby="chi-siamo-titolo">
      <div className="container">
        <SectionHead numero="02" titolo="Chi siamo" id="chi-siamo" />
        <p className="statement" data-reveal>
          Agenzia Castelli Romani
        </p>
      </div>
    </section>
  );
}

/** Immagini dei servizi: render Cycles dello stesso mondo 3D della home (appartamento dimostrativo). */
const IMMAGINI_SERVIZI: Record<string, string> = {
  compravendita: 'Il portone del palazzo al tramonto (render 3D)',
  'tecnologia-360': 'Il salone dell’appartamento dimostrativo, visitabile a 360 gradi (render 3D)',
  'affitto-protetto': 'Ingresso con porta blindata (render 3D)',
  valutazioni: 'Planimetria 3D in sezione dell’appartamento dimostrativo (render 3D)',
  'affitto-concordato': 'Cucina con isola (render 3D)',
};

const Visita360 = lazy(() => import('../components/Visita360'));

export function Servizi() {
  const [visita, setVisita] = useState(false);
  return (
    <section id="servizi" className="section section--ink" aria-labelledby="servizi-titolo">
      <div className="container">
        <SectionHead numero="03" titolo="I nostri servizi" id="servizi" />
        <ul className="servizi">
          {SERVIZI.map((s) => (
            <li key={s.id} className="servizio" data-reveal>
              <div className="servizio__media">
                <img
                  src={`/images/servizi/${s.id}.webp`}
                  alt={IMMAGINI_SERVIZI[s.id]}
                  loading="lazy"
                  width={1200}
                  height={750}
                />
                {s.id === 'tecnologia-360' && (
                  <button type="button" className="servizio__360" onClick={() => setVisita(true)}>
                    <span aria-hidden="true">360°</span> Prova la visita virtuale
                  </button>
                )}
              </div>
              <div className="servizio__body">
                <h3 className="servizio__title">{s.titolo}</h3>
                <p className="servizio__text">{s.testo}</p>
              </div>
            </li>
          ))}
        </ul>
        <p className="servizi__nota">Le immagini sono render 3D dell’appartamento dimostrativo mostrato nella home.</p>
      </div>
      {visita && (
        <Suspense fallback={null}>
          <Visita360 src="/images/servizi/salone-360.webp" onClose={() => setVisita(false)} />
        </Suspense>
      )}
    </section>
  );
}

const IconPhone = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z" /></svg>
);
const IconWhatsapp = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.15l-.3-.18-3 .78.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.25-.12-1.47-.72-1.7-.8-.23-.09-.4-.13-.56.12-.17.25-.64.8-.79.97-.14.16-.29.18-.54.06a6.7 6.7 0 0 1-3.3-2.9c-.25-.43.25-.4.71-1.33.08-.16.04-.3-.02-.42l-.76-1.83c-.2-.48-.4-.41-.56-.42h-.47a.9.9 0 0 0-.66.31 2.8 2.8 0 0 0-.86 2.07 4.8 4.8 0 0 0 1 2.55 11 11 0 0 0 4.2 3.7c1.57.68 2.18.73 2.97.62.48-.07 1.47-.6 1.68-1.18.2-.58.2-1.08.14-1.18-.06-.1-.22-.17-.47-.29z" /></svg>
);
const IconMail = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm9 7.3L4.2 7v10h15.6V7z" /></svg>
);
const IconFacebook = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13.5 21v-7.5H16l.4-3h-2.9V8.6c0-.87.25-1.46 1.5-1.46h1.55V4.45A21 21 0 0 0 14.3 4.3c-2.2 0-3.7 1.34-3.7 3.8v2.4H8v3h2.6V21z" /></svg>
);

export function Contatti() {
  const voci = [
    { label: 'Chiama', valore: CONTATTI.telefonoVisibile, href: CONTATTI.telefonoHref, icon: <IconPhone />, esterno: false },
    { label: 'WhatsApp', valore: CONTATTI.telefonoVisibile, href: CONTATTI.whatsappHref, icon: <IconWhatsapp />, esterno: true },
    { label: 'E-mail', valore: CONTATTI.email, href: CONTATTI.emailHref, icon: <IconMail />, esterno: false },
    { label: 'Facebook', valore: 'Domus Re', href: CONTATTI.facebookHref, icon: <IconFacebook />, esterno: true },
  ];
  return (
    <section id="contatti" className="section section--ink" aria-labelledby="contatti-titolo">
      <div className="container">
        <SectionHead numero="05" titolo="Contatti" id="contatti" />
        <ul className="contatti">
          {voci.map((v) => (
            <li key={v.label} data-reveal>
              <a
                className="contatto"
                href={v.href}
                {...(v.esterno ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
              >
                <span className="contatto__icon">{v.icon}</span>
                <span className="contatto__label">{v.label}</span>
                <span className="contatto__value">{v.valore}</span>
                <span className="contatto__arrow" aria-hidden="true">→</span>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function Approfondimenti() {
  return (
    <section id="approfondimenti" className="section section--ink" aria-labelledby="approfondimenti-titolo">
      <div className="container">
        <SectionHead numero="07" titolo="Approfondimenti" id="approfondimenti" />
        <p className="statement statement--light" data-reveal>
          Arriveranno presto
        </p>
      </div>
    </section>
  );
}

export function DoveCiTroviamo() {
  return (
    <section id="dove-ci-troviamo" className="section section--stone" aria-labelledby="dove-ci-troviamo-titolo">
      <div className="container dove">
        <div className="dove__text">
          <SectionHead numero="08" titolo="Dove ci troviamo" id="dove-ci-troviamo" />
          <address className="dove__address" data-reveal>
            <span className="dove__street">{AGENZIA.indirizzo}</span>
            <span>
              {AGENZIA.cap} {AGENZIA.citta} {AGENZIA.provincia}
            </span>
          </address>
          <div className="dove__actions" data-reveal>
            <a className="pill pill--gold" href={MAPS_URL} target="_blank" rel="noopener noreferrer">
              Apri in Google Maps
            </a>
            <a className="pill pill--outline" href={MAPS_DIREZIONI_URL} target="_blank" rel="noopener noreferrer">
              Indicazioni stradali
            </a>
          </div>
        </div>
        <a className="dove__photo" href={MAPS_URL} target="_blank" rel="noopener noreferrer" data-reveal>
          <img
            src="/images/sede-domus-re.webp"
            alt={`La sede di Domus Re Immobiliare in ${INDIRIZZO_COMPLETO}`}
            loading="lazy"
            width={1179}
            height={858}
          />
        </a>
      </div>
    </section>
  );
}
