import { useEffect, useState } from 'react';
import { ORARI, type Fascia } from '../data/site';

const fmt = (min: number) => `${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`;

/** Giorno (0 = lunedì) e minuti correnti nel fuso orario di Roma, indipendentemente dal fuso del visitatore. */
function adessoARoma() {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Rome',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date());
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '';
  const giorni = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  return { giorno: giorni.indexOf(get('weekday')), minuti: Number(get('hour')) * 60 + Number(get('minute')) };
}

function stato(giorno: number, minuti: number) {
  const fasce = ORARI[giorno].fasce;
  const corrente = fasce.find(([a, c]) => minuti >= a && minuti < c);
  if (corrente) return { aperto: true, testo: `Aperto ora · chiude alle ${fmt(corrente[1])}` };
  const prossima = fasce.find(([a]) => minuti < a);
  if (prossima) return { aperto: false, testo: `Chiuso ora · apre alle ${fmt(prossima[0])}` };
  for (let i = 1; i <= 7; i++) {
    const g = (giorno + i) % 7;
    if (ORARI[g].fasce.length) {
      const quando = i === 1 ? 'domani' : ORARI[g].giorno.toLowerCase();
      return { aperto: false, testo: `Chiuso ora · riapre ${quando} alle ${fmt(ORARI[g].fasce[0][0])}` };
    }
  }
  return { aperto: false, testo: 'Chiuso' };
}

const fasceTesto = (fasce: readonly Fascia[]) => (fasce.length ? fasce.map(([a, c]) => `${fmt(a)} – ${fmt(c)}`) : ['Chiuso']);

export function Orari() {
  const [now, setNow] = useState(adessoARoma);
  useEffect(() => {
    const t = window.setInterval(() => setNow(adessoARoma()), 30_000);
    return () => window.clearInterval(t);
  }, []);
  const s = stato(now.giorno, now.minuti);

  return (
    <section id="orari" className="section section--stone" aria-labelledby="orari-titolo">
      <div className="container">
        <header className="section-head" data-reveal>
          <span className="section-head__num">06</span>
          <h2 id="orari-titolo" className="section-head__title">
            Orari
          </h2>
        </header>

        <p className={`orari__stato ${s.aperto ? 'is-open' : ''}`} data-reveal role="status">
          <span className="orari__dot" aria-hidden="true" />
          {s.testo}
        </p>

        <table className="orari" data-reveal>
          <caption className="visually-hidden">Orari di apertura dell’agenzia</caption>
          <tbody>
            {ORARI.map((o, i) => (
              <tr key={o.giorno} className={i === now.giorno ? 'is-today' : ''} aria-current={i === now.giorno ? 'date' : undefined}>
                <th scope="row">{o.giorno}</th>
                {fasceTesto(o.fasce).map((f, j, arr) => (
                  <td key={j} colSpan={arr.length === 1 ? 2 : 1} className={o.fasce.length ? '' : 'is-closed'}>
                    {f}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
