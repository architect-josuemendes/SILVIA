# obsidian_vault.py
# Generates linked Obsidian notes from SILVIA observations
# The graph view = visual representation of the Digital Twin
# Josue Mendes - 2024/2026
#
# Each observation creates interconnected notes:
#   observation -> species, locations, practices, TRI snapshot, observer
# Graph density = DT maturity (shadow -> embryonic -> juvenile -> mature)

import os
import re
from datetime import datetime

DEFAULT_VAULT_PATH = os.getenv('SILVIA_VAULT_PATH', './silvia_vault')

VAULT_DIRS = [
    'observations', 'entities/species', 'entities/locations',
    'entities/practices', 'tri', 'observers', 'communities', '_meta'
]

PRIORITY_TAGS = {
    'critical': '#silvia/priority/critical', 'high': '#silvia/priority/high',
    'medium': '#silvia/priority/medium', 'low': '#silvia/priority/low'
}
HEALTH_TAGS = {
    'critical_degradation': '#silvia/health/critical-degradation',
    'degradation': '#silvia/health/degradation',
    'stable': '#silvia/health/stable',
    'regeneration': '#silvia/health/regeneration'
}

COMMUNITIES = {
    'pemon_kanaimo': {
        'title': 'Kanaimö — Pueblo Pemón',
        'region': 'Gran Sabana, Bolívar, Venezuela',
        'dt_maturity': 'embryonic',
        'description': 'Territorio ancestral del pueblo Pemón. Ecosistema de sabana, tepuyes y bosque de galería.'
    },
    'caracas_urban': {
        'title': 'Caracas Metropolitana',
        'region': 'Distrito Capital, Venezuela',
        'dt_maturity': 'shadow',
        'description': 'Area metropolitana con asentamientos informales, corredores ecologicos urbanos y patrimonio historico.'
    },
    'bayerischer_wald': {
        'title': 'Nationalpark Bayerischer Wald',
        'region': 'Bavaria, Deutschland',
        'dt_maturity': 'mature',
        'description': 'Parque nacional con gestion de rewilding, monitoreo de Borkenkäfer y datos forestales extensivos.'
    }
}


class ObsidianVault:

    def __init__(self, vault_path=DEFAULT_VAULT_PATH):
        self.vault_path = vault_path
        self._init_vault()

    def _init_vault(self):
        for d in VAULT_DIRS:
            os.makedirs(os.path.join(self.vault_path, d), exist_ok=True)
        # create community index notes
        for mod_id, info in COMMUNITIES.items():
            path = os.path.join(self.vault_path, 'communities', f"{mod_id}.md")
            if not os.path.exists(path):
                self._write(path, self._community_template(mod_id, info))

    # -- main entry point --

    def record_observation(self, result):
        """Record a SILVIA result as linked Obsidian notes."""
        data = result.get('data', {})
        tri = result.get('tri', {})
        session = result.get('session', {})
        ts = datetime.now()

        if data.get('error') or not data.get('acknowledgment'):
            return {'notes_created': []}
        if data.get('needs_clarification', False):
            return {'notes_created': []}

        created = []

        # entities (species, locations, practices)
        entity_links = self._record_entities(data, session, ts)
        created.extend(entity_links.get('created', []))

        # observer
        sender = session.get('sender', 'unknown')
        obs_path = self._record_observer(sender, session, ts)
        if obs_path:
            created.append(obs_path)

        # TRI snapshot
        tri_path = None
        if tri:
            tri_path = self._record_tri(tri, session, ts)
            created.append(tri_path)

        # main observation note
        obs_note = self._record_observation_note(data, tri, session, ts, entity_links, tri_path, sender)
        created.append(obs_note)

        # backlink in community note
        community = session.get('community')
        if community:
            comm_path = os.path.join(self.vault_path, 'communities', f"{community}.md")
            if os.path.exists(comm_path):
                obs_name = os.path.basename(obs_note).replace('.md', '')
                self._append(comm_path, f"- {ts.strftime('%Y-%m-%d %H:%M')} → [[{obs_name}]]\n")

        # dashboard
        self._update_dashboard(ts)

        return {'notes_created': created, 'observation_note': obs_note, 'timestamp': ts.isoformat()}

    # -- observation note --

    def _record_observation_note(self, data, tri, session, ts, entity_links, tri_path, sender):
        ts_str = ts.strftime('%Y%m%d_%H%M%S') + f"_{ts.microsecond:06d}"
        community = session.get('community', 'unknown')
        priority = data.get('priority', 'medium')
        health = tri.get('health_status', 'unknown') if tri else 'unknown'
        score = tri.get('score', 0) if tri else 0

        filename = f"OBS_{ts_str}_{community}.md"
        path = os.path.join(self.vault_path, 'observations', filename)

        # wikilinks
        sp_links = [f"[[{s}]]" for s in entity_links.get('species', [])]
        loc_links = [f"[[{l}]]" for l in entity_links.get('locations', [])]
        prac_links = [f"[[{p}]]" for p in entity_links.get('practices', [])]
        community_link = f"[[{community}]]"
        observer_link = f"[[observer_{self._slug(sender)}]]"
        tri_link = f"[[{os.path.basename(tri_path).replace('.md', '')}]]" if tri_path else "N/A"

        # care flags (might come as dicts from claude)
        care_flags = data.get('care_flags', [])
        care_flags_str = [f if isinstance(f, str) else f.get('flag', f.get('type', str(f))) for f in care_flags]
        care_line = ', '.join(f"`{x}`" for x in care_flags_str) if care_flags_str else 'ninguno'

        recs = data.get('recommendations', {})
        do_lines = '\n'.join(f"  - {item}" for item in recs.get('do', []))
        dont_lines = '\n'.join(f"  - {item}" for item in recs.get('dont', []))

        content = f"""---
type: observation
date: {ts.strftime('%Y-%m-%d')}
time: {ts.strftime('%H:%M:%S')}
community: {community}
observer: {sender}
priority: {priority}
tri_score: {score}
health_status: {health}
care_flags: [{', '.join(care_flags_str)}]
tags:
  - silvia/observation
  - {PRIORITY_TAGS.get(priority, '#silvia/priority/unknown')}
  - {HEALTH_TAGS.get(health, '#silvia/health/unknown')}
---

# Observacion {ts_str}

**Comunidad:** {community_link}
**Observador:** {observer_link}
**Prioridad:** {priority.upper()}
**TRI:** {tri_link}

## Reconocimiento

{data.get('acknowledgment', '')}

## Entidades detectadas

**Especies:** {' · '.join(sp_links) if sp_links else 'ninguna detectada'}
**Ubicaciones:** {' · '.join(loc_links) if loc_links else 'ninguna detectada'}
**Practicas:** {' · '.join(prac_links) if prac_links else 'ninguna detectada'}

### Temporal
- Texto original: {data.get('entities_detected', {}).get('temporal', {}).get('raw_text', 'N/A')}
- Estacion local: {data.get('entities_detected', {}).get('temporal', {}).get('local_season', 'N/A')}

## Interpretacion territorial

{data.get('territorial_interpretation', '')}

## TRI Inputs

| Variable | Valor | Nota |
|----------|-------|------|
| ESD | {data.get('tri_inputs', {}).get('esd_raw', 'N/A')} | Ecosystem Services Diversity |
| TCI | {data.get('tri_inputs', {}).get('tci_raw', 'N/A')} | Territorial Cultural Integrity |
| RAR | {data.get('tri_inputs', {}).get('rar_raw', 'N/A')} | Regeneration-to-Alteration |
| IIS | {tri.get('variables', {}).get('iis', 'N/A') if tri else 'N/A'} | Info Sovereignty ({tri.get('variables', {}).get('iis_source', 'N/A') if tri else 'N/A'}) |
| **TRI** | **{score}** | **{health}** |

## Recomendaciones

**Hacer:**
{do_lines if do_lines else '  - (ninguna)'}

**Evitar:**
{dont_lines if dont_lines else '  - (ninguna)'}

## CARE Flags

{care_line}

---
*SILVIA v0.3.0 · {ts.isoformat()}*
"""
        self._write(path, content)
        return path

    # -- entity notes --

    def _record_entities(self, data, session, ts):
        entities = data.get('entities_detected', {})
        community = session.get('community', 'unknown')
        created = []
        links = {'species': [], 'locations': [], 'practices': [], 'created': []}

        # species - claude sometimes returns dicts instead of strings
        for item in entities.get('species', []):
            if isinstance(item, dict):
                species = item.get('name_reported', item.get('name', str(item)))
            else:
                species = str(item)
            slug = self._slug(species)
            name = f"sp_{slug}"
            links['species'].append(name)
            path = os.path.join(self.vault_path, 'entities', 'species', f"{name}.md")
            if not os.path.exists(path):
                self._write(path, self._species_template(species, community, ts))
                created.append(path)
            else:
                self._append_sighting(path, community, ts)

        # location
        loc_raw = entities.get('location', {})
        loc_text = loc_raw.get('raw_text', '') if isinstance(loc_raw, dict) else str(loc_raw)
        if loc_text:
            slug = self._slug(loc_text)
            name = f"loc_{slug}"
            links['locations'].append(name)
            path = os.path.join(self.vault_path, 'entities', 'locations', f"{name}.md")
            coords = loc_raw.get('coordinates_if_available') if isinstance(loc_raw, dict) else None
            if not os.path.exists(path):
                self._write(path, self._location_template(loc_text, community, ts, coords))
                created.append(path)
            else:
                self._append_sighting(path, community, ts)

        # practices (from actions)
        for item in entities.get('actions', []):
            if isinstance(item, dict):
                action = item.get('action', item.get('name', str(item)))
            else:
                action = str(item)
            slug = self._slug(action)
            name = f"prac_{slug}"
            links['practices'].append(name)
            path = os.path.join(self.vault_path, 'entities', 'practices', f"{name}.md")
            if not os.path.exists(path):
                self._write(path, self._practice_template(action, community, ts))
                created.append(path)
            else:
                self._append_sighting(path, community, ts)

        links['created'] = created
        return links

    # -- observer note --

    def _record_observer(self, sender, session, ts):
        slug = self._slug(sender)
        name = f"observer_{slug}"
        path = os.path.join(self.vault_path, 'observers', f"{name}.md")
        community = session.get('community', 'unknown')
        role = session.get('observer_role', 'unknown')

        if not os.path.exists(path):
            content = f"""---
type: observer
sender_id: {sender}
role: {role}
first_seen: {ts.strftime('%Y-%m-%d')}
communities: [{community}]
observation_count: 1
tags:
  - silvia/observer
  - silvia/role/{role}
---

# Observador: {sender}

**Rol:** {role}
**Primera observacion:** {ts.strftime('%Y-%m-%d %H:%M')}
**Comunidad:** [[{community}]]

## Historial

- {ts.strftime('%Y-%m-%d %H:%M')} — primera interaccion

"""
            self._write(path, content)
        else:
            self._append(path, f"- {ts.strftime('%Y-%m-%d %H:%M')} — observacion en [[{community}]]\n")
            self._increment_frontmatter(path, 'observation_count')
        return path

    # -- TRI snapshot --

    def _record_tri(self, tri, session, ts):
        ts_str = ts.strftime('%Y%m%d_%H%M%S') + f"_{ts.microsecond:06d}"
        community = session.get('community', 'unknown')
        path = os.path.join(self.vault_path, 'tri', f"TRI_{ts_str}_{community}.md")

        v = tri.get('variables', {})
        w = tri.get('weights_used', {})

        content = f"""---
type: tri_snapshot
date: {ts.strftime('%Y-%m-%d')}
community: {community}
tri_score: {tri.get('score', 0)}
health_status: {tri.get('health_status', 'unknown')}
tags:
  - silvia/tri
  - {HEALTH_TAGS.get(tri.get('health_status', ''), '#silvia/health/unknown')}
---

# TRI {ts.strftime('%Y-%m-%d %H:%M')}

**Comunidad:** [[{community}]]
**Score:** {tri.get('score', 0)}
**Estado:** {tri.get('health_status', 'unknown')}
**XP:** {tri.get('xp', 0)}

## Variables

```
ESD:  {v.get('esd', 0)}
TCI:  {v.get('tci', 0)}
RAR:  {v.get('rar_raw', 0)} (norm: {v.get('rar_normalized', 0)})
IIS:  {v.get('iis', 0)} ({v.get('iis_source', 'unknown')})
```

## Pesos: {w.get('source', 'default')}

`TRI = ({w.get('w_esd', 0.25)}*{v.get('esd', 0)}) + ({w.get('w_tci', 0.25)}*{v.get('tci', 0)}) + ({w.get('w_rar', 0.30)}*{v.get('rar_normalized', 0)}) + ({w.get('w_iis', 0.20)}*{v.get('iis', 0)}) = {tri.get('score', 0)}`

---
*SILVIA v0.3.0*
"""
        self._write(path, content)
        return path

    # -- dashboard --

    def _update_dashboard(self, ts):
        path = os.path.join(self.vault_path, '_meta', 'dashboard.md')
        stats = {}
        for d in VAULT_DIRS:
            dp = os.path.join(self.vault_path, d)
            if os.path.isdir(dp):
                stats[d] = len([f for f in os.listdir(dp) if f.endswith('.md')])

        total = stats.get('observations', 0)
        if total == 0: maturity = 'shadow'
        elif total < 50: maturity = 'embryonic'
        elif total < 500: maturity = 'juvenile'
        else: maturity = 'mature'

        content = f"""---
type: dashboard
updated: {ts.isoformat()}
tags: [silvia/meta]
---

# SILVIA Dashboard

*Actualizado: {ts.strftime('%Y-%m-%d %H:%M')}*

## Estado del Digital Twin

| Metrica | Valor |
|---------|-------|
| Observaciones | {stats.get('observations', 0)} |
| Especies | {stats.get('entities/species', 0)} |
| Ubicaciones | {stats.get('entities/locations', 0)} |
| Practicas | {stats.get('entities/practices', 0)} |
| Snapshots TRI | {stats.get('tri', 0)} |
| Observadores | {stats.get('observers', 0)} |
| Comunidades | {stats.get('communities', 0)} |

## Madurez: **{maturity.upper()}** ({total} observaciones)

> Abre Graph View (Cmd+G) para ver las conexiones.
> Densidad del grafo = madurez del DT.

## Navegacion

- [[pemon_kanaimo|Kanaimö — Pueblo Pemón]]
- [[caracas_urban|Caracas Metropolitana]]
- [[bayerischer_wald|Nationalpark Bayerischer Wald]]

---
*SILVIA v0.3.0*
"""
        self._write(path, content)

    # -- templates --

    def _community_template(self, mod_id, info):
        return f"""---
type: community
module_id: {mod_id}
region: {info['region']}
dt_maturity: {info['dt_maturity']}
tags: [silvia/community, silvia/dt/{info['dt_maturity']}]
---

# {info['title']}

**Region:** {info['region']}
**Madurez DT:** {info['dt_maturity']}

{info['description']}

## Observaciones recientes

"""

    def _species_template(self, species, community, ts):
        return f"""---
type: species
name: {species}
first_seen: {ts.strftime('%Y-%m-%d')}
communities: [{community}]
sighting_count: 1
tags: [silvia/entity/species]
---

# {species}

**Primera observacion:** {ts.strftime('%Y-%m-%d')}
**Comunidad:** [[{community}]]

## Avistamientos

- {ts.strftime('%Y-%m-%d %H:%M')} — [[{community}]]

"""

    def _location_template(self, location, community, ts, coords=None):
        coords_line = f"**Coordenadas:** {coords}" if coords else "**Coordenadas:** no disponibles"
        return f"""---
type: location
name: {location}
first_seen: {ts.strftime('%Y-%m-%d')}
communities: [{community}]
tags: [silvia/entity/location]
---

# {location}

**Primera mencion:** {ts.strftime('%Y-%m-%d')}
**Comunidad:** [[{community}]]
{coords_line}

## Observaciones

- {ts.strftime('%Y-%m-%d %H:%M')} — [[{community}]]

"""

    def _practice_template(self, practice, community, ts):
        return f"""---
type: practice
name: {practice}
first_seen: {ts.strftime('%Y-%m-%d')}
communities: [{community}]
tags: [silvia/entity/practice]
---

# {practice}

**Primera mencion:** {ts.strftime('%Y-%m-%d')}
**Comunidad:** [[{community}]]

## Observaciones

- {ts.strftime('%Y-%m-%d %H:%M')} — [[{community}]]

"""

    # -- utils --

    @staticmethod
    def _slug(text):
        s = text.lower().strip()
        s = re.sub(r'[^\w\s-]', '', s)
        s = re.sub(r'[\s_]+', '_', s)
        return s.strip('_')[:80]

    @staticmethod
    def _write(path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def _append(path, content):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def _append_sighting(path, community, ts):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"- {ts.strftime('%Y-%m-%d %H:%M')} — [[{community}]]\n")

    @staticmethod
    def _increment_frontmatter(path, field):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            pattern = rf'({field}:\s*)(\d+)'
            match = re.search(pattern, content)
            if match:
                content = re.sub(pattern, f'{match.group(1)}{int(match.group(2)) + 1}', content)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
        except (IOError, ValueError):
            pass


# -- standalone test --
if __name__ == '__main__':
    print("Testing vault...")
    vault = ObsidianVault('./test_vault')

    mock = {
        'data': {
            'acknowledgment': 'Observacion registrada desde el Roraima.',
            'community_context': {'module_loaded': 'pemon_kanaimo'},
            'observer_context': {'inferred_role': 'community_member', 'confidence': 0.8},
            'priority': 'medium',
            'entities_detected': {
                'species': ['tucán', 'danta'],
                'actions': ['avistamiento de fauna'],
                'location': {'raw_text': 'sendero al Roraima', 'normalized': 'Roraima-tepui', 'coordinates_if_available': None},
                'temporal': {'raw_text': 'esta mañana', 'local_season': 'Kononnö', 'approximate_date': '2026-03'}
            },
            'territorial_interpretation': 'Corredor ecologico funcional entre bosque de galeria y dosel tepuyano.',
            'tri_inputs': {'esd_raw': 0.7, 'tci_raw': 0.6, 'rar_raw': 0.3, 'iis_raw': 0.7},
            'recommendations': {'do': ['Continuar monitoreo'], 'dont': ['No ampliar sendero']},
            'care_flags': [],
            'needs_clarification': False,
        },
        'tri': {
            'score': 0.62, 'health_status': 'regeneration', 'priority': 'low',
            'variables': {'esd': 0.7, 'tci': 0.6, 'rar_raw': 0.3, 'rar_normalized': 0.65, 'iis': 0.7, 'iis_source': 'community_member'},
            'weights_used': {'source': 'pemon_kanaimo', 'w_esd': 0.25, 'w_tci': 0.25, 'w_rar': 0.30, 'w_iis': 0.20},
            'alert': False, 'xp': 50
        },
        'session': {
            'community': 'pemon_kanaimo', 'dt_maturity': 'embryonic',
            'observer_role': 'community_member', 'observation_count': 1,
            'sender': 'whatsapp:+58412XXXXXXX'
        }
    }

    result = vault.record_observation(mock)
    print(f"Notes created: {len(result['notes_created'])}")
    for n in result['notes_created']:
        print(f"  {n}")
    print("Done")

    import shutil
    shutil.rmtree('./test_vault', ignore_errors=True)
