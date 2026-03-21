# tri_engine.py
# TRI (Territorial Regeneration Index) calculator
# Josue Mendes - 2024/2026
#
# Based on: Berkes (2008), Mang & Reed (2012), Niemi & McDonald (2004)
# TRI = w1*ESD + w2*TCI + w3*RAR_norm + w4*IIS

# Default weights - these are working hypotheses, not validated empirically yet
# Community modules can override them
DEFAULT_WEIGHTS = {
    'w_esd': 0.25,
    'w_tci': 0.25,
    'w_rar': 0.30,  # RAR highest because Mang & Reed argue regeneration capacity is most predictive
    'w_iis': 0.20
}

# Per-community overrides
MODULE_WEIGHTS = {
    'pemon_kanaimo': {
        'w_esd': 0.25,
        'w_tci': 0.25,
        'w_rar': 0.30,
        'w_iis': 0.20
    },
    'caracas_urban': {
        'w_esd': 0.25,
        'w_tci': 0.30,  # cultural integrity pesa mas en asentamientos informales
        'w_rar': 0.25,
        'w_iis': 0.20
    }
}

# IIS based on observer role - replaces the old hardcoded 0.60
# The whole point of SILVIA is that WHO reports matters
IIS_BY_ROLE = {
    'community_leader':   1.0,
    'community_member':   0.7,
    'field_researcher':   0.5,
    'institutional':      0.4,
    'external_observer':  0.3,
    'unknown':            0.1
}

# XP rewards - incentivize reporting problems over stability
XP_TABLE = {
    'critical':     150,
    'degradation':  100,
    'regeneration':  50,
    'stable':        25,
}


def calculate_tri(tri_inputs, observer_role='unknown', community_module=None):
    """Main TRI calculation. Returns score + metadata."""

    # extract and clamp inputs
    esd = _clamp(float(tri_inputs.get('esd_raw', 0.5)), 0.0, 1.0)
    tci = _clamp(float(tri_inputs.get('tci_raw', 0.5)), 0.0, 1.0)
    rar = _clamp(float(tri_inputs.get('rar_raw', 0.0)), -1.0, 1.0)

    # IIS from observer role, not hardcoded anymore
    iis = IIS_BY_ROLE.get(observer_role, 0.1)

    # normalize RAR from [-1,1] to [0,1] so the weighted sum works
    rar_norm = (rar + 1) / 2

    # load weights
    weights = MODULE_WEIGHTS.get(community_module, DEFAULT_WEIGHTS)
    w1, w2, w3, w4 = weights['w_esd'], weights['w_tci'], weights['w_rar'], weights['w_iis']

    # composite score
    tri = (w1 * esd) + (w2 * tci) + (w3 * rar_norm) + (w4 * iis)
    tri = round(_clamp(tri, 0.0, 1.0), 3)

    # health status - this is ecological state, NOT dt lifecycle
    if rar < -0.5:
        health_status = 'critical_degradation'
    elif rar < 0.0:
        health_status = 'degradation'
    elif rar < 0.3:
        health_status = 'stable'
    else:
        health_status = 'regeneration'

    # auto-escalation
    if tri < 0.30 or health_status == 'critical_degradation':
        priority = 'critical'
    elif tri < 0.40 or health_status == 'degradation':
        priority = 'high'
    elif tri < 0.60:
        priority = 'medium'
    else:
        priority = 'low'

    # gamification
    if health_status == 'critical_degradation':
        xp = XP_TABLE['critical']
    elif health_status == 'degradation':
        xp = XP_TABLE['degradation']
    elif health_status == 'regeneration':
        xp = XP_TABLE['regeneration']
    else:
        xp = XP_TABLE['stable']

    return {
        'score': tri,
        'health_status': health_status,
        'priority': priority,
        'variables': {
            'esd': round(esd, 2),
            'tci': round(tci, 2),
            'rar_raw': round(rar, 2),
            'rar_normalized': round(rar_norm, 2),
            'iis': round(iis, 2),
            'iis_source': observer_role
        },
        'weights_used': {
            'source': community_module or 'default',
            'w_esd': w1, 'w_tci': w2, 'w_rar': w3, 'w_iis': w4
        },
        'alert': priority in ('critical', 'high'),
        'xp': xp
    }


def _clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))


# -- tests --
if __name__ == '__main__':

    print("=" * 60)
    print("TEST 1: Capitan Pemon reporta incendio descontrolado")
    print("=" * 60)
    result = calculate_tri(
        tri_inputs={'esd_raw': 0.3, 'tci_raw': 0.2, 'rar_raw': -0.8},
        observer_role='community_leader',
        community_module='pemon_kanaimo'
    )
    print(f"  TRI:      {result['score']}")
    print(f"  Health:   {result['health_status']}")
    print(f"  Priority: {result['priority']}")
    print(f"  IIS:      {result['variables']['iis']} ({result['variables']['iis_source']})")
    print(f"  Alert:    {result['alert']}")
    print(f"  XP:       {result['xp']}")
    assert result['priority'] == 'critical'
    assert result['alert'] is True
    assert result['xp'] == 150
    assert result['variables']['iis'] == 1.0
    print("  PASSED\n")

    print("=" * 60)
    print("TEST 2: Turista reporta tucanes en Roraima")
    print("=" * 60)
    result = calculate_tri(
        tri_inputs={'esd_raw': 0.7, 'tci_raw': 0.5, 'rar_raw': 0.2},
        observer_role='external_observer',
        community_module='pemon_kanaimo'
    )
    print(f"  TRI:      {result['score']}")
    print(f"  Health:   {result['health_status']}")
    print(f"  Priority: {result['priority']}")
    print(f"  IIS:      {result['variables']['iis']} ({result['variables']['iis_source']})")
    assert result['variables']['iis'] == 0.3
    assert result['alert'] is False
    print("  PASSED\n")

    print("=" * 60)
    print("TEST 3: Vecino de Petare reporta crecida de quebrada")
    print("=" * 60)
    result = calculate_tri(
        tri_inputs={'esd_raw': 0.2, 'tci_raw': 0.4, 'rar_raw': -0.6},
        observer_role='community_member',
        community_module='caracas_urban'
    )
    print(f"  TRI:      {result['score']}")
    print(f"  Health:   {result['health_status']}")
    print(f"  Priority: {result['priority']}")
    print(f"  Weights:  {result['weights_used']}")
    assert result['priority'] in ('critical', 'high')
    assert result['alert'] is True
    assert result['weights_used']['source'] == 'caracas_urban'
    print("  PASSED\n")

    print("=" * 60)
    print("TEST 4: Comunidad desconocida (shadow mode)")
    print("=" * 60)
    result = calculate_tri(
        tri_inputs={'esd_raw': 0.5, 'tci_raw': 0.5, 'rar_raw': 0.0},
        observer_role='unknown',
        community_module=None
    )
    print(f"  TRI:      {result['score']}")
    print(f"  IIS:      {result['variables']['iis']} ({result['variables']['iis_source']})")
    assert result['weights_used']['source'] == 'default'
    assert result['variables']['iis'] == 0.1
    print("  PASSED\n")

    print("=" * 60)
    print("TEST 5: Edge case - max values")
    print("=" * 60)
    result = calculate_tri(
        tri_inputs={'esd_raw': 1.0, 'tci_raw': 1.0, 'rar_raw': 1.0},
        observer_role='community_leader',
        community_module='pemon_kanaimo'
    )
    print(f"  TRI: {result['score']}  (max possible = 1.0)")
    assert result['score'] == 1.0
    print("  PASSED\n")

    print("=" * 60)
    print("TEST 6: Edge case - min values")
    print("=" * 60)
    result = calculate_tri(
        tri_inputs={'esd_raw': 0.0, 'tci_raw': 0.0, 'rar_raw': -1.0},
        observer_role='unknown',
        community_module=None
    )
    print(f"  TRI: {result['score']}  (min possible = 0.02)")
    assert result['score'] == 0.02
    assert result['priority'] == 'critical'
    print("  PASSED\n")

    print("ALL TESTS PASSED")
