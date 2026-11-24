import logoUrl from '../assets/logo-domus-re.svg';

/** Marchio (chiocciola-casa) reso in oro metallico tramite maschera CSS sul tracciato vettoriale. */
export function LogoMark({ className = '' }: { className?: string }) {
  return (
    <span
      className={`logo-mark ${className}`}
      style={{ '--logo-url': `url("${logoUrl}")` } as React.CSSProperties}
      role="img"
      aria-label="Logo Domus Re"
    />
  );
}

export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <span className={`wordmark ${compact ? 'wordmark--compact' : ''}`}>
      <span className="wordmark__name">Domus Re</span>
      <span className="wordmark__sub">Immobiliare</span>
    </span>
  );
}
