import { createContext, useContext } from 'react';

export type ScrollToFn = (id: string) => void;
export const ScrollContext = createContext<ScrollToFn>(() => {});
export const useScrollTo = () => useContext(ScrollContext);
