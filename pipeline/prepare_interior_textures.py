"""Tinte dei materiali interni dell'appartamento (da texture fotografiche Poly Haven)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare_city_textures import tint_img, save, tx  # noqa: E402

save(tint_img(tx('white_plaster_02', 'white_plaster_02_diff_1k.jpg'), (232, 226, 214), 0.35), 'intonaco_interno_diff.jpg')
save(tint_img(tx('marble_01', 'marble_01_diff_2k.jpg'), (226, 222, 214), 0.6), 'marmo_chiaro_diff.jpg')
save(tint_img(tx('marble_01', 'marble_01_diff_2k.jpg'), (236, 232, 224), 0.45), 'marmo_camino_diff.jpg')
save(tint_img(tx('velour_velvet', 'velour_velvet_diff_1k.jpg'), (118, 102, 86), 0.8), 'velluto_tortora_diff.jpg')
save(tint_img(tx('rough_linen', 'rough_linen_diff_1k.jpg'), (226, 220, 208), 0.6), 'lino_diff.jpg')
save(tint_img(tx('rough_linen', 'rough_linen_diff_1k.jpg'), (176, 160, 136), 0.9), 'tappeto_diff.jpg')
save(tint_img(tx('oak_veneer_01', 'oak_veneer_01_diff_1k.jpg'), (150, 118, 84), 0.9), 'rovere_diff.jpg')
save(tint_img(tx('herringbone_parquet', 'herringbone_parquet_diff_1k.jpg'), (176, 140, 102), 0.85), 'parquet_rovere_diff.jpg')
save(tint_img(tx('rough_linen', 'rough_linen_diff_1k.jpg'), (194, 184, 168), 0.7), 'tessuto_divano_diff.jpg')
