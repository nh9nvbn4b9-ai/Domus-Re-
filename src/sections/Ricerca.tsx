import { useId, useMemo, useState } from 'react';
import { CITTA, CONTATTI, whatsappConTesto } from '../data/site';
import { FASCE_BUDGET, IMMOBILI, type Contratto, type Immobile, type TipoImmobile } from '../data/immobili';

type Giardino = 'indifferente' | 'si' | 'no';
type Tipo = 'indifferente' | TipoImmobile;

interface Filtri {
  contratto: Contratto;
  citta: string;
  budget: string;
  giardino: Giardino;
  tipo: Tipo;
}

const INIZIALI: Filtri = { contratto: 'acquisto', citta: '', budget: '', giardino: 'indifferente', tipo: 'indifferente' };

const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });

function filtra(f: Filtri): Immobile[] {
  const fascia = FASCE_BUDGET[f.contratto].find((b) => b.id === f.budget);
  return IMMOBILI.filter(
    (i) =>
      i.contratto === f.contratto &&
      (!f.citta || i.citta === f.citta) &&
      (!fascia || (i.prezzo >= fascia.min && i.prezzo <= fascia.max)) &&
      (f.giardino === 'indifferente' || i.giardino === (f.giardino === 'si')) &&
      (f.tipo === 'indifferente' || i.tipo === f.tipo),
  );
}

function messaggio(f: Filtri) {
  const fascia = FASCE_BUDGET[f.contratto].find((b) => b.id === f.budget);
  const parti = [
    `Buongiorno, cerco ${f.tipo === 'indifferente' ? 'un immobile' : f.tipo === 'villa' ? 'una villa' : 'un appartamento'}`,
    f.contratto === 'affitto' ? 'in affitto' : 'da acquistare',
    f.citta ? `a ${f.citta}` : 'nei Castelli Romani',
    fascia ? `con budget ${fascia.label.toLowerCase()}` : '',
    f.giardino === 'si' ? 'con giardino' : f.giardino === 'no' ? 'senza giardino' : '',
  ];
  return parti.filter(Boolean).join(' ') + '.';
}

function Segmented<T extends string>({
  name,
  value,
  options,
  onChange,
  legend,
}: {
  name: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  legend: string;
}) {
  return (
    <fieldset className="segmented">
      <legend className="field__label">{legend}</legend>
      <div className="segmented__track">
        {options.map((o) => (
          <label key={o.value} className={`segmented__opt ${value === o.value ? 'is-active' : ''}`}>
            <input type="radio" name={name} value={o.value} checked={value === o.value} onChange={() => onChange(o.value)} />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function Ricerca() {
  const [f, setF] = useState<Filtri>(INIZIALI);
  const [avanzata, setAvanzata] = useState(false);
  const [cercato, setCercato] = useState(false);
  const ids = { citta: useId(), budget: useId(), adv: useId() };
  const risultati = useMemo(() => filtra(f), [f]);
  const set = <K extends keyof Filtri>(k: K, v: Filtri[K]) => setF((prev) => ({ ...prev, [k]: v }));

  return (
    <section id="ricerca" className="section section--stone" aria-labelledby="ricerca-titolo">
      <div className="container">
        <header className="section-head" data-reveal>
          <span className="section-head__num">04</span>
          <h2 id="ricerca-titolo" className="section-head__title">
            Ricerca appartamenti
          </h2>
        </header>

        <form
          className="search"
          data-reveal
          onSubmit={(e) => {
            e.preventDefault();
            setCercato(true);
          }}
        >
          <div className="search__grid">
            <Segmented
              legend="Tipologia"
              name="contratto"
              value={f.contratto}
              onChange={(v) => setF((p) => ({ ...p, contratto: v, budget: '' }))}
              options={[
                { value: 'acquisto', label: 'Acquisto' },
                { value: 'affitto', label: 'Affitto' },
              ]}
            />

            <div className="field">
              <label className="field__label" htmlFor={ids.citta}>
                Città
              </label>
              <select id={ids.citta} className="field__control" value={f.citta} onChange={(e) => set('citta', e.target.value)}>
                <option value="">Tutte le città</option>
                {CITTA.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label className="field__label" htmlFor={ids.budget}>
                Budget
              </label>
              <select id={ids.budget} className="field__control" value={f.budget} onChange={(e) => set('budget', e.target.value)}>
                <option value="">Qualsiasi budget</option>
                {FASCE_BUDGET[f.contratto].map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.label}
                  </option>
                ))}
              </select>
            </div>

            <button type="submit" className="pill pill--gold search__submit">
              Cerca
            </button>
          </div>

          <button
            type="button"
            className="search__adv-toggle"
            aria-expanded={avanzata}
            aria-controls={ids.adv}
            onClick={() => setAvanzata((v) => !v)}
          >
            <span>Ricerca avanzata</span>
            <span className="search__adv-icon" aria-hidden="true">
              {avanzata ? '−' : '+'}
            </span>
          </button>

          <div id={ids.adv} className={`search__adv ${avanzata ? 'is-open' : ''}`} hidden={!avanzata}>
            <Segmented
              legend="Giardino"
              name="giardino"
              value={f.giardino}
              onChange={(v) => set('giardino', v)}
              options={[
                { value: 'indifferente', label: 'Indifferente' },
                { value: 'si', label: 'Con giardino' },
                { value: 'no', label: 'Senza giardino' },
              ]}
            />
            <Segmented
              legend="Tipo di immobile"
              name="tipo"
              value={f.tipo}
              onChange={(v) => set('tipo', v)}
              options={[
                { value: 'indifferente', label: 'Indifferente' },
                { value: 'appartamento', label: 'Appartamento' },
                { value: 'villa', label: 'Villa' },
              ]}
            />
          </div>
        </form>

        <div className="results" aria-live="polite">
          {cercato &&
            (risultati.length ? (
              <ul className="results__grid">
                {risultati.map((i) => (
                  <li key={i.id} className="listing">
                    {i.foto[0] && <img src={i.foto[0]} alt={i.titolo} loading="lazy" />}
                    <div className="listing__body">
                      <p className="listing__meta">
                        {i.citta} · {i.mq} m² · {i.locali} locali
                      </p>
                      <h3 className="listing__title">{i.titolo}</h3>
                      <p className="listing__price">
                        {euro.format(i.prezzo)}
                        {i.contratto === 'affitto' ? ' /mese' : ''}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="results__empty">
                <p className="results__empty-title">Nessun immobile pubblicato corrisponde alla ricerca.</p>
                <p>Raccontaci cosa cerchi: ti proponiamo noi le soluzioni più adatte.</p>
                <div className="results__actions">
                  <a className="pill pill--gold" href={whatsappConTesto(messaggio(f))} target="_blank" rel="noopener noreferrer">
                    Scrivici su WhatsApp
                  </a>
                  <a className="pill pill--outline" href={CONTATTI.telefonoHref}>
                    Chiama
                  </a>
                </div>
              </div>
            ))}
        </div>
      </div>
    </section>
  );
}
