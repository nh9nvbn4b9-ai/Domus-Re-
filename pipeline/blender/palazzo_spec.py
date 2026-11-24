"""Misure del palazzo ricavate dalla fotografia di riferimento (reference/palazzo-riferimento.jpg, 836x1672 px).

Ogni quota è annotata in pixel della foto e convertita in metri con una sola scala S.
La foto è una vista frontale raddrizzata (verticali parallele): le proporzioni sul piano
di facciata sono affidabili. La scala è fissata in modo che le porte dell'atrio siano ~2,5 m
e l'interpiano ~3,9 m.

Questo modulo è la fonte unica dei dati dell'edificio: build_palazzo.py lo usa per modellare,
e write_json() esporta la griglia (piani, assi, aperture) per il sito (src/data/palazzo.json),
che servirà anche per l'appartamento: le finestre viste da fuori sono le stesse dell'interno.
"""
import json
import os

S = 62.0      # px per metro
X0 = 423.0    # asse di simmetria (px)
Y0 = 1655.0   # quota del marciapiede (px)


def X(px):
    return (px - X0) / S


def Z(py):
    return (Y0 - py) / S


def L(px):
    return px / S


HALF_W = L(381)           # facciata: x 42..804 px
DEPTH = 16.0              # profondità dell'edificio (non visibile in foto)
WALL_T = 0.60             # spessore muro di facciata
GLASS_Y = 0.24            # piano dei vetri (arretrato nel muro)

# --- Piano terra -----------------------------------------------------------
GROUND = {
    'pilaster_x': [-L(329), -L(131), L(131), L(329)],    # lesene scanalate (centri)
    'pedestal_top': Z(1560), 'pedestal_w': L(78),
    'shaft_w': L(56), 'shaft_top': Z(1280),
    'capital_top': Z(1230), 'capital_w': L(84),
    'frieze_top': Z(1218),
    'cornice_top': Z(1170),                                # 7,82 m
    'cornice_half_w': L(398),
    'arches': [                                            # aperture ad arco: centro, larghezza, sommità
        {'x': -L(227), 'w': L(97), 'top': Z(1282)},
        {'x': 0.0, 'w': L(145), 'top': Z(1282)},
        {'x': L(227), 'w': L(97), 'top': Z(1282)},
    ],
    'transom_low': Z(1490), 'transom_high': Z(1460),
}

# --- Ordine gigante (piani 1-4) ----------------------------------------------
UPPER = {
    'outer_col_x': L(335), 'outer_col_r': L(21),
    'inner_col_x': L(133), 'inner_col_r': L(17),
    'col_pedestal_top': Z(1080), 'col_base_top': Z(1065),
    'outer_capital_bottom': Z(365), 'outer_capital_top': Z(335),
    'inner_capital_bottom': Z(530), 'inner_capital_top': Z(505),
    'frieze_bottom': Z(330), 'cornice_bottom': Z(300), 'cornice_top': Z(272),
    'side_bay_x': L(231.5), 'side_win_w': L(80),
    'course_h': L(22.5),                                   # bugnato: altezza dei corsi
}

# Piani: quota del pavimento = base delle portefinestre laterali.
FLOORS = [
    {'n': 1, 'level': Z(1170), 'win_top': Z(1085)},       # mezzanino, in parte nascosto dal cornicione
    {'n': 2, 'level': Z(1010), 'win_top': Z(868), 'railing_top': Z(985),
     'balustrade': (Z(1052), Z(1015)), 'panel': (Z(1080), Z(1057))},
    {'n': 3, 'level': Z(770), 'win_top': Z(625), 'railing_top': Z(740),
     'balustrade': (Z(810), Z(772)), 'panel': (Z(855), Z(825))},
    {'n': 4, 'level': Z(527), 'win_top': Z(405), 'railing_top': Z(500),
     'balustrade': (Z(570), Z(530)), 'panel': (Z(615), Z(577))},
]
ATTIC_BALUSTRADE = (Z(370), Z(335))

CENTRAL = {
    # piano 2: finestra sopra la lunetta
    'c2_win': {'w': L(145), 'bottom': Z(1000), 'top': Z(870), 'transom': Z(902)},
    'lunette': {'cz': Z(1170), 'r_out': L(157), 'r_in': L(125)},
    # piano 3: portafinestra sul grande balcone con balaustra (piano dell'appartamento)
    'c3_win': {'w': L(145), 'bottom': Z(785), 'top': Z(620), 'transom': Z(652)},
    'c3_balcony': {'half_w': L(130), 'floor': Z(785), 'rail_top': Z(735),
                   'slab_bottom': Z(855), 'slab_half_w': L(122), 'depth': 1.05},
    # piano 4: finestra ad arco con balconcino in ferro su mensola in pietra
    'c4_win': {'w': L(153), 'bottom': Z(550), 'top': Z(390)},
    'c4_balcony': {'half_w': L(92), 'floor': Z(550), 'rail_top': Z(505),
                   'base_bottom': Z(610), 'base_half_w': L(95), 'depth': 0.55},
    'arch_frame': {'cz': Z(480), 'r_out': L(165), 'r_in': L(130)},
}

MANSARD = {
    'eave': UPPER['cornice_top'],      # 22,31 m
    'curb_bottom': Z(125), 'curb_top': Z(85),
    'setback': 0.75,                   # arretramento della falda in sommità
    'side_dormer_x': L(231.5), 'dormer_w': L(57), 'dormer_top': Z(205),
    'dormer_surround_w': L(108), 'dormer_surround_top': Z(172),
    'pavilion_half_w': L(170), 'pavilion_top': Z(70),
    'pav_win_w': L(128), 'pav_win_top': Z(140), 'pav_win_bottom': Z(270),
    'pav_balustrade_top': Z(228), 'pav_impost': Z(195),
}

STREET = {'sidewalk_w': 6.0, 'road_w': 9.0, 'lamp_x': [-L(398), L(392)], 'lamp_y': -2.1}

# Appartamento dimostrativo: piano 3, quello del grande balcone centrale.
APARTMENT_FLOOR = 3


def write_json(path):
    f3 = next(f for f in FLOORS if f['n'] == APARTMENT_FLOOR)
    data = {
        '_nota': 'Generato da pipeline/blender/palazzo_spec.py — non modificare a mano.',
        'scala_px_per_m': S,
        'facciata': {'mezza_larghezza': HALF_W, 'profondita': DEPTH, 'spessore_muro': WALL_T, 'piano_vetri': GLASS_Y},
        'piani': [{'n': f['n'], 'quota': round(f['level'], 3), 'sommita_finestre': round(f['win_top'], 3)} for f in FLOORS],
        'assi_finestre': {'laterali': [-UPPER['side_bay_x'], UPPER['side_bay_x']], 'centrale': 0.0,
                          'larghezza_laterali': UPPER['side_win_w'], 'larghezza_centrale': CENTRAL['c3_win']['w']},
        'appartamento': {
            'piano': APARTMENT_FLOOR, 'quota_pavimento': round(f3['level'], 3),
            'portafinestra_balcone': {'x': 0.0, 'larghezza': CENTRAL['c3_win']['w'],
                                      'base': CENTRAL['c3_win']['bottom'], 'sommita': CENTRAL['c3_win']['top']},
            'balcone': {'mezza_larghezza': CENTRAL['c3_balcony']['half_w'], 'quota': CENTRAL['c3_balcony']['floor'],
                        'profondita': CENTRAL['c3_balcony']['depth']},
            'finestre_laterali': [{'x': s * UPPER['side_bay_x'], 'larghezza': UPPER['side_win_w'],
                                   'base': f3['level'], 'sommita': f3['win_top']} for s in (-1, 1)],
        },
        'altezza_totale': round(MANSARD['pavilion_top'], 3),
        'luci': light_rig(),
        'camere': {
            # inquadratura iniziale: più lontana della foto, palazzo ~80% dell'altezza
            # coordinate web (Y in alto, Z verso la strada); centro_y = quota del centro quadro sulla facciata
            'hero': {'pos': [0.0, 1.7, 36.0], 'fov_v': 47.0, 'centro_y': 15.0},
            'foto': {'pos': [0.0, 1.6, 40.0], 'fov_v': 37.7, 'centro_y': 13.4},
        },
    }
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def light_rig():
    """Luci d'accento come in foto: uplight alla base di colonne e lesene, faretti nel sottocornicione,
    lanterne dei lampioni. Coordinate in metri, sistema Blender (x, y, z) con y verso l'interno."""
    ups = []
    for x in GROUND['pilaster_x']:
        ups.append({'pos': [x, -0.53, GROUND['pedestal_top'] + 0.02], 'dir': [0, 0.07, 1], 'tipo': 'uplight'})
    for x in (-UPPER['outer_col_x'], UPPER['outer_col_x']):
        ups.append({'pos': [x, -0.70, UPPER['col_pedestal_top'] + 0.02], 'dir': [0, 0.05, 1], 'tipo': 'uplight'})
    for x in (-UPPER['inner_col_x'], UPPER['inner_col_x']):
        ups.append({'pos': [x, -0.58, UPPER['col_pedestal_top'] + 0.02], 'dir': [0, 0.05, 1], 'tipo': 'uplight'})
    downs = []
    for a in GROUND['arches']:
        downs.append({'pos': [a['x'], -0.55, GROUND['capital_top'] - 0.02], 'dir': [0, 0, -1], 'tipo': 'downlight'})
    lamps = [{'pos': [x, STREET['lamp_y'], 3.55], 'tipo': 'lanterna'} for x in STREET['lamp_x']]
    return ups + downs + lamps


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'data', 'palazzo.json')
    write_json(out)
    print('scritto', os.path.abspath(out))
