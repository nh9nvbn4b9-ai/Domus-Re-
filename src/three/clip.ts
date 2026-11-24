import { Plane, Vector3 } from 'three';
import { PALAZZO } from './coords';

/**
 * Piano di sezione per la planimetria 3D: taglia il palazzo poco sopra il pavimento del 3° piano
 * (la balaustra del balcone resta intera). Fuori dalla planimetria è spostato molto in alto.
 */
export const SECTION = new Plane(new Vector3(0, -1, 0), 1e5);
export const SECTION_HEIGHT = PALAZZO.appartamento_pianta.quota + 0.6;
export const setSection = (on: boolean) => {
  SECTION.constant = on ? SECTION_HEIGHT : 1e5;
};
