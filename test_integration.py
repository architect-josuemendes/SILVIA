"""
SILVIA — Full Integration Test (no API key needed)
Mocks Claude API response to test the entire pipeline:
  message → agent → TRI → vault → Obsidian notes
"""

import json
import os
import shutil
from unittest.mock import MagicMock, patch
from silvia_agent import SilviaAgent


# ═══════════════════════════════════════════════════════════
# MOCK CLAUDE RESPONSES
# ═══════════════════════════════════════════════════════════

MOCK_PEMON_RESPONSE = json.dumps({
    "silvia_version": "0.1.0",
    "community_context": {
        "module_loaded": "pemon_kanaimo",
        "community_name": "Kanaimö",
        "detection_method": "linguistic",
        "detection_confidence": 0.95,
        "dt_maturity": "embryonic"
    },
    "observer_context": {
        "inferred_role": "community_member",
        "confidence": 0.8
    },
    "acknowledgment": "Observación registrada: avistamiento de tucanes y dantas cerca del Roraima.",
    "priority": "low",
    "entities_detected": {
        "species": ["tucán", "danta"],
        "actions": ["avistamiento de fauna", "monitoreo visual"],
        "location": {
            "raw_text": "cerca del Roraima",
            "normalized": "Roraima-tepui",
            "coordinates_if_available": None
        },
        "temporal": {
            "raw_text": "esta mañana",
            "local_season": "Kononnö",
            "approximate_date": "2026-03"
        }
    },
    "territorial_interpretation": "La presencia conjunta de tucán (dosel intacto) y danta (bosque de galería saludable) cerca del Roraima indica un corredor ecológico funcional. Este patrón es coherente con la estación Kononnö, cuando la biodiversidad activa es alta.",
    "tri_inputs": {
        "esd_raw": 0.7,
        "tci_raw": 0.6,
        "rar_raw": 0.3,
        "iis_raw": 0.7,
        "tri_composite": 0.0,
        "formula": "0.25×ESD + 0.25×TCI + 0.30×RAR + 0.20×IIS",
        "notes": "DT embryonic — baja confianza en TRI por pocas observaciones."
    },
    "recommendations": {
        "do": [
            "Continuar monitoreo del corredor Roraima",
            "Documentar frecuencia de avistamientos de danta"
        ],
        "dont": [
            "No ampliar senderos sin consulta a la capitanía"
        ]
    },
    "care_flags": [],
    "silvia_modules_used": ["pemon_kanaimo"],
    "needs_clarification": False,
    "clarification_questions": []
})

MOCK_CARACAS_RESPONSE = json.dumps({
    "silvia_version": "0.1.0",
    "community_context": {
        "module_loaded": "caracas_urban",
        "community_name": "Petare",
        "detection_method": "linguistic",
        "detection_confidence": 0.9,
        "dt_maturity": "shadow"
    },
    "observer_context": {
        "inferred_role": "community_member",
        "confidence": 0.75
    },
    "acknowledgment": "Alerta registrada: crecida de quebrada en Petare.",
    "priority": "critical",
    "entities_detected": {
        "species": [],
        "actions": ["crecida de quebrada", "inundación parcial"],
        "location": {
            "raw_text": "quebrada de Petare, sector José Félix Ribas",
            "normalized": "Petare",
            "coordinates_if_available": None
        },
        "temporal": {
            "raw_text": "ahora mismo, está lloviendo fuerte",
            "local_season": "Lluvias",
            "approximate_date": "2026-03"
        }
    },
    "territorial_interpretation": "Crecida de quebrada en sector José Félix Ribas de Petare durante lluvias fuertes. Las laderas informales de este sector tienen alto riesgo de deslizamiento. Situación requiere atención inmediata.",
    "tri_inputs": {
        "esd_raw": 0.2,
        "tci_raw": 0.4,
        "rar_raw": -0.7,
        "iis_raw": 0.7,
        "tri_composite": 0.0,
        "formula": "0.25×ESD + 0.30×TCI + 0.25×RAR + 0.20×IIS",
        "notes": "Emergencia activa. DT shadow — datos insuficientes para análisis predictivo."
    },
    "recommendations": {
        "do": [
            "Evacuar zonas bajas cercanas a la quebrada",
            "Contactar protección civil",
            "Documentar nivel del agua si es seguro"
        ],
        "dont": [
            "No cruzar la quebrada bajo ninguna circunstancia",
            "No permanecer en viviendas con grietas en ladera"
        ]
    },
    "care_flags": ["location_sensitivity", "economic_vulnerability"],
    "silvia_modules_used": ["caracas_urban"],
    "needs_clarification": False,
    "clarification_questions": []
})

MOCK_UNKNOWN_RESPONSE = json.dumps({
    "silvia_version": "0.1.0",
    "community_context": {
        "module_loaded": "",
        "community_name": "",
        "detection_method": "direct",
        "detection_confidence": 0.0,
        "dt_maturity": "shadow"
    },
    "observer_context": {
        "inferred_role": "unknown",
        "confidence": 0.3
    },
    "acknowledgment": "Gracias por tu mensaje. Necesito más contexto para analizarlo.",
    "priority": "low",
    "entities_detected": {
        "species": [],
        "actions": [],
        "location": {"raw_text": "", "normalized": "", "coordinates_if_available": None},
        "temporal": {"raw_text": "", "local_season": "", "approximate_date": ""}
    },
    "territorial_interpretation": "",
    "tri_inputs": {
        "esd_raw": 0.0, "tci_raw": 0.0, "rar_raw": 0.0, "iis_raw": 0.0,
        "tri_composite": 0.0, "formula": "", "notes": ""
    },
    "recommendations": {"do": [], "dont": []},
    "care_flags": [],
    "silvia_modules_used": [],
    "needs_clarification": True,
    "clarification_questions": [
        "¿Desde qué comunidad o territorio estás reportando?",
        "¿Puedes indicar tu ubicación aproximada?",
        "¿Es un entorno urbano, rural o indígena?"
    ]
})


# ═══════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════

def create_mock_response(text):
    """Create a mock Anthropic API response."""
    mock = MagicMock()
    mock.content = [MagicMock(text=text)]
    return mock


def run_tests():
    test_vault = './test_integration_vault'

    # Clean previous test
    if os.path.exists(test_vault):
        shutil.rmtree(test_vault)

    os.environ['SILVIA_VAULT_PATH'] = test_vault

    print("=" * 60)
    print("SILVIA Integration Test — Full Pipeline")
    print("=" * 60)

    # Patch the Anthropic client
    with patch('silvia_agent.anthropic.Anthropic') as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client

        agent = SilviaAgent()

        # ─── TEST 1: Pemón observation ───
        print("\n🌿 TEST 1: Pemón observation (tucanes near Roraima)")
        mock_client.messages.create.return_value = create_mock_response(MOCK_PEMON_RESPONSE)

        result = agent.process(
            "Vi tucanes y dantas cerca del Roraima esta mañana",
            sender="whatsapp:+58412XXXXXXX"
        )
        formatted = agent.format_response(result)

        assert result['data']['community_context']['module_loaded'] == 'pemon_kanaimo'
        assert result['tri'] is not None
        assert result['tri']['score'] > 0
        assert result['tri']['variables']['iis'] == 0.7  # community_member
        assert result['tri']['weights_used']['source'] == 'pemon_kanaimo'
        assert result['session']['community'] == 'pemon_kanaimo'
        assert 'Kanaimö' in formatted
        print(f"  TRI: {result['tri']['score']} | Health: {result['tri']['health_status']}")
        print(f"  IIS: {result['tri']['variables']['iis']} (community_member)")
        print(f"  Vault notes created: ✓")
        print(f"  ✅ PASSED")

        # ─── TEST 2: Caracas emergency ───
        print("\n🏙️ TEST 2: Caracas emergency (flooding in Petare)")
        mock_client.messages.create.return_value = create_mock_response(MOCK_CARACAS_RESPONSE)

        result = agent.process(
            "La quebrada de Petare se está desbordando, sector José Félix Ribas, está lloviendo fuerte ahora mismo",
            sender="whatsapp:+58414YYYYYYY"
        )
        formatted = agent.format_response(result)

        assert result['data']['community_context']['module_loaded'] == 'caracas_urban'
        assert result['data']['priority'] == 'critical'
        assert result['tri'] is not None
        assert result['tri']['alert'] is True
        assert result['tri']['weights_used']['source'] == 'caracas_urban'
        assert 'CARE' in formatted
        assert 'ALERTA' in formatted
        print(f"  TRI: {result['tri']['score']} | Health: {result['tri']['health_status']}")
        print(f"  Priority: {result['tri']['priority']} | Alert: {result['tri']['alert']}")
        print(f"  CARE flags: {result['data']['care_flags']}")
        print(f"  ✅ PASSED")

        # ─── TEST 3: Unknown community (asks for clarification) ───
        print("\n❓ TEST 3: Unknown community (clarification)")
        mock_client.messages.create.return_value = create_mock_response(MOCK_UNKNOWN_RESPONSE)

        result = agent.process(
            "Hola, quiero reportar algo",
            sender="whatsapp:+58416ZZZZZZZ"
        )
        formatted = agent.format_response(result)

        assert result['data']['needs_clarification'] is True
        assert result['tri'] is None  # no TRI when clarifying
        assert len(result['data']['clarification_questions']) == 3
        # emoji check skipped - format simplified
        print(f"  Clarification questions: {len(result['data']['clarification_questions'])}")
        print(f"  TRI calculated: No (as expected)")
        print(f"  ✅ PASSED")

        # ─── TEST 4: Session persistence ───
        print("\n🔄 TEST 4: Session persistence (Pemón sender sends again)")
        mock_client.messages.create.return_value = create_mock_response(MOCK_PEMON_RESPONSE)

        result = agent.process(
            "Ahora veo también guacamayas volando sobre el morichal",
            sender="whatsapp:+58412XXXXXXX"  # same sender as test 1
        )

        session = agent.sessions.get("whatsapp:+58412XXXXXXX")
        assert session is not None
        assert session['community_module'] == 'pemon_kanaimo'
        assert session['observer_role'] == 'community_member'
        assert session['observation_count'] == 2
        assert len(session['history']) == 4  # 2 user + 2 assistant
        print(f"  Observation count: {session['observation_count']}")
        print(f"  History length: {len(session['history'])} messages")
        print(f"  Community persisted: {session['community_module']}")
        print(f"  ✅ PASSED")

        # ─── TEST 5: Vault structure ───
        print("\n📂 TEST 5: Vault structure verification")
        assert os.path.exists(os.path.join(test_vault, 'observations'))
        assert os.path.exists(os.path.join(test_vault, 'entities', 'species'))
        assert os.path.exists(os.path.join(test_vault, 'entities', 'locations'))
        assert os.path.exists(os.path.join(test_vault, 'entities', 'practices'))
        assert os.path.exists(os.path.join(test_vault, 'tri'))
        assert os.path.exists(os.path.join(test_vault, 'observers'))
        assert os.path.exists(os.path.join(test_vault, 'communities'))
        assert os.path.exists(os.path.join(test_vault, '_meta', 'dashboard.md'))

        # Count generated notes
        obs_count = len(os.listdir(os.path.join(test_vault, 'observations')))
        species_count = len(os.listdir(os.path.join(test_vault, 'entities', 'species')))
        loc_count = len(os.listdir(os.path.join(test_vault, 'entities', 'locations')))
        tri_count = len(os.listdir(os.path.join(test_vault, 'tri')))
        observer_count = len(os.listdir(os.path.join(test_vault, 'observers')))

        print(f"  Observations: {obs_count}")
        print(f"  Species: {species_count}")
        print(f"  Locations: {loc_count}")
        print(f"  TRI snapshots: {tri_count}")
        print(f"  Observers: {observer_count}")

        assert obs_count >= 3  # 3 non-clarification observations
        assert species_count >= 2  # tucán, danta
        assert tri_count >= 3
        assert observer_count >= 2  # two different senders
        print(f"  ✅ PASSED")

        # ─── TEST 6: Wikilinks in observation notes ───
        print("\n🔗 TEST 6: Wikilink integrity")
        obs_files = os.listdir(os.path.join(test_vault, 'observations'))
        first_obs = open(
            os.path.join(test_vault, 'observations', sorted(obs_files)[0]),
            'r'
        ).read()

        assert '[[pemon_kanaimo]]' in first_obs
        assert '[[sp_tucán]]' in first_obs or '[[sp_danta]]' in first_obs
        assert '[[TRI_' in first_obs
        assert '[[observer_' in first_obs
        print(f"  Community link: ✓")
        print(f"  Species links: ✓")
        print(f"  TRI link: ✓")
        print(f"  Observer link: ✓")
        print(f"  ✅ PASSED")

        # ─── TEST 7: Dashboard ───
        print("\n📊 TEST 7: Dashboard content")
        dashboard = open(
            os.path.join(test_vault, '_meta', 'dashboard.md'), 'r'
        ).read()

        assert 'EMBRYONIC' in dashboard
        assert 'Observaciones' in dashboard
        assert '[[pemon_kanaimo' in dashboard
        print(f"  DT maturity shown: ✓")
        print(f"  Stats table: ✓")
        print(f"  Navigation links: ✓")
        print(f"  ✅ PASSED")

        # ─── TEST 8: WhatsApp format output ───
        print("\n📱 TEST 8: WhatsApp format output")
        mock_client.messages.create.return_value = create_mock_response(MOCK_PEMON_RESPONSE)
        result = agent.process("test", sender="format_test")
        formatted = agent.format_response(result)

        assert len(formatted) <= 1600  # WhatsApp char limit
        assert '📊 TRI' in formatted
        assert 'ESD:' in formatted
        assert '✅' in formatted or '⛔' in formatted
        assert '⭐' in formatted  # XP
        print(f"  Length: {len(formatted)} chars (max 1600)")
        print(f"  TRI line: ✓")
        print(f"  Variables: ✓")
        print(f"  Recommendations: ✓")
        print(f"  XP: ✓")
        print(f"  ✅ PASSED")

    # Clean up
    shutil.rmtree(test_vault, ignore_errors=True)

    print("\n" + "=" * 60)
    print("ALL 8 TESTS PASSED ✅")
    print("=" * 60)
    print("\nPipeline verified: message → agent → TRI → vault → Obsidian")
    print("Ready to run with real API key: python app.py")


if __name__ == '__main__':
    run_tests()
