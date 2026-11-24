import { Component, type ReactNode } from 'react';

/**
 * Contenitore per parti della scena caricate in background (città, appartamento):
 * se un file non si carica, la scena principale continua a funzionare senza quella parte.
 */
export class Facoltativo extends Component<{ children: ReactNode; nome: string }, { errore: boolean }> {
  state = { errore: false };

  static getDerivedStateFromError() {
    return { errore: true };
  }

  componentDidCatch(err: unknown) {
    console.warn(`[scena] ${this.props.nome} non disponibile`, err);
  }

  render() {
    return this.state.errore ? null : this.props.children;
  }
}
