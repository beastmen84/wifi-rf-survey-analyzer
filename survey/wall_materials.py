"""Stable material/style identifiers; descriptive only, without RF coefficients."""
# material: (light fill, ink, default schematic pattern)
MATERIALS = {
    'unspecified': ('#d1d5db', '#64748b', 'solid'),
    'wood': ('#f0dfbc', '#896b3f', 'wood'),
    'clay_block': ('#f4d8c8', '#a26952', 'grid'),
    'brick': ('#edc9bb', '#9d5e4c', 'brick'),
    'concrete_block': ('#dce1e5', '#73818c', 'brick'),
    'aerated_concrete': ('#eef0e7', '#8b9480', 'dots'),
    'drywall': ('#e6e9f2', '#8a91ac', 'diagonal'),
    'concrete': ('#d6d9dc', '#7a828a', 'dots'),
    'reinforced_concrete': ('#cbd1d8', '#627182', 'cross'),
    'stone': ('#e2dbcd', '#90816b', 'brick'),
    'glass': ('#e0f3f6', '#6da5b1', 'diagonal'),
    'metal': ('#d7e3ea', '#637e91', 'cross'),
    'insulation': ('#f4eac5', '#ac9651', 'wood'),
}
PATTERNS = ('auto', 'solid', 'diagonal', 'cross', 'dots', 'brick', 'grid', 'wood')


def appearance(wall):
    return wall.get('material', 'unspecified'), wall.get('pattern', 'auto')


def validated_appearance(value):
    if not isinstance(value, dict) or not set(value) <= {'material', 'pattern'}:
        raise ValueError('wall_invalid_material')
    material, pattern = appearance(value)
    if not isinstance(material, str) or material not in MATERIALS or not isinstance(pattern, str) or pattern not in PATTERNS:
        raise ValueError('wall_invalid_material')
    # Old files and explicit defaults compare identically after normalization.
    return {k:v for k,v,default in (('material',material,'unspecified'),('pattern',pattern,'auto')) if v != default}
