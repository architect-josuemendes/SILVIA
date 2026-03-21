# silvia_agent.py
# SILVIA core agent - handles community detection, prompt composition, and TRI
# Josue Mendes - 2024/2026

import os
import json
import logging
from dotenv import load_dotenv
import anthropic

from tri_engine import calculate_tri
from obsidian_vault import ObsidianVault

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvia')

MAX_HISTORY = 20  # ~10 turns before we start trimming
CORE_PROMPT_PATH = 'prompts/silvia_core.txt'
MODULES_DIR = 'community_modules'

AVAILABLE_MODULES = {
    'pemon_kanaimo': {
        'file': 'pemon_kanaimo.txt',
        'dt_maturity': 'embryonic',
        'display_name': 'Kanaimö · Pueblo Pemón'
    },
    'caracas_urban': {
        'file': 'caracas_urban.txt',
        'dt_maturity': 'shadow',
        'display_name': 'Caracas Metropolitana'
    },
    'bayerischer_wald': {
        'file': 'bayerischer_wald.txt',
        'dt_maturity': 'mature',
        'display_name': 'Nationalpark Bayerischer Wald'
    }
}


class SilviaAgent:

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.core_prompt = self._load_file(CORE_PROMPT_PATH)
        self.module_cache = {}
        self.sessions = {}
        self.vault = ObsidianVault(os.getenv('SILVIA_VAULT_PATH', './silvia_vault'))

    # -- session management --

    def _get_session(self, sender):
        if sender not in self.sessions:
            self.sessions[sender] = {
                'history': [],
                'community_module': None,
                'dt_maturity': 'shadow',
                'observer_role': 'unknown',
                'observation_count': 0
            }
        return self.sessions[sender]

    def _trim_history(self, session):
        if len(session['history']) > MAX_HISTORY:
            session['history'] = session['history'][-MAX_HISTORY:]

    # -- dynamic prompt composition --
    # this is the key architectural piece: core + community module
    # the prompt changes depending on which community is active

    def _build_system_prompt(self, session):
        prompt = self.core_prompt
        module_id = session['community_module']
        if module_id and module_id in AVAILABLE_MODULES:
            module_text = self._load_module(module_id)
            if module_text:
                prompt += "\n\n" + module_text
        return prompt

    def _load_module(self, module_id):
        if module_id not in self.module_cache:
            info = AVAILABLE_MODULES.get(module_id)
            if not info:
                return None
            path = os.path.join(MODULES_DIR, info['file'])
            self.module_cache[module_id] = self._load_file(path)
        return self.module_cache.get(module_id)

    # -- main processing --

    def process(self, message, sender="test"):
        session = self._get_session(sender)
        session['history'].append({"role": "user", "content": message})
        self._trim_history(session)

        system_prompt = self._build_system_prompt(session)

        # call claude
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_prompt,
                messages=session['history']
            )
            raw = response.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return self._error_response("Error de conexion con SILVIA. Intenta de nuevo.")

        session['history'].append({"role": "assistant", "content": raw})

        # parse json
        data = self._parse_json(raw)
        if data is None:
            logger.warning(f"Failed to parse JSON from Claude: {raw[:200]}")
            return self._error_response(
                "SILVIA no pudo procesar la respuesta. Intenta reformular tu observacion."
            )

        # update session context from response
        self._update_session(session, data)

        # calculate TRI only if we have enough info
        tri_result = None
        if not data.get('needs_clarification', False):
            tri_result = calculate_tri(
                tri_inputs=data.get('tri_inputs', {}),
                observer_role=session['observer_role'],
                community_module=session['community_module']
            )
            session['observation_count'] += 1

        result = {
            'data': data,
            'tri': tri_result,
            'session': {
                'community': session['community_module'],
                'dt_maturity': session['dt_maturity'],
                'observer_role': session['observer_role'],
                'observation_count': session['observation_count'],
                'sender': sender
            }
        }

        # write to obsidian vault (non-blocking)
        try:
            vault_result = self.vault.record_observation(result)
            logger.info(f"Vault: {len(vault_result.get('notes_created', []))} notes created/updated")
        except Exception as e:
            logger.error(f"Vault recording error: {e}", exc_info=True)

        return result

    def _update_session(self, session, data):
        """Pull community + observer info from Claude's response into session."""
        community = data.get('community_context', {})
        module_id = community.get('module_loaded', '')
        if module_id and module_id in AVAILABLE_MODULES:
            if session['community_module'] != module_id:
                session['community_module'] = module_id
                session['dt_maturity'] = AVAILABLE_MODULES[module_id]['dt_maturity']
                logger.info(f"Community detected: {module_id}")

        observer = data.get('observer_context', {})
        role = observer.get('inferred_role', 'unknown')
        confidence = observer.get('confidence', 0.0)
        if confidence >= 0.5 and role != 'unknown':
            session['observer_role'] = role

    # -- format for whatsapp --

    def format_response(self, result):
        data = result['data']
        tri = result['tri']
        session = result.get('session', {})

        # clarification mode
        if data.get('needs_clarification'):
            lines = [data.get('acknowledgment', ''), ""]
            for q in data.get('clarification_questions', []):
                lines.append(f"  {q}")
            return "\n".join(lines)

        # resolve community name
        community_id = session.get('community', None)
        if community_id and community_id in AVAILABLE_MODULES:
            community_name = AVAILABLE_MODULES[community_id]['display_name']
        else:
            community_name = "Territorio desconocido"

        priority_emoji = {
            'critical': '\U0001f534', 'high': '\U0001f7e0',
            'medium': '\U0001f7e1', 'low': '\U0001f7e2'
        }
        p = priority_emoji.get(data.get('priority', 'medium'), '')

        lines = [
            data.get('acknowledgment', ''),
            "",
            f"\U0001f4ca TRI {community_name}: {tri['score']} "
            f"{p} {tri['health_status'].replace('_', ' ').title()}",
            f"   ESD: {tri['variables']['esd']} \u00b7 "
            f"TCI: {tri['variables']['tci']} \u00b7 "
            f"RAR: {tri['variables']['rar_raw']} \u00b7 "
            f"IIS: {tri['variables']['iis']} ({tri['variables']['iis_source']})",
            "",
            data.get('territorial_interpretation', ''),
        ]

        # recommendations
        recs = data.get('recommendations', {})
        for item in recs.get('do', []):
            lines.append(f"\u2705 {item}")
        for item in recs.get('dont', []):
            lines.append(f"\u26d4 {item}")

        # care flags
        care = data.get('care_flags', [])
        if care:
            care_str = [c if isinstance(c, str) else c.get('flag', c.get('type', str(c))) for c in care]
            lines.append(f"\U0001f6e1\ufe0f CARE: {', '.join(care_str)}")

        if tri.get('xp'):
            lines.append(f"\u2b50 +{tri['xp']} XP")

        if tri.get('alert'):
            lines.append("\u26a0\ufe0f ALERTA TERRITORIAL")

        return "\n".join(lines)

    # -- utils --

    def _parse_json(self, raw):
        """Try to get valid JSON from Claude's response, handling markdown fences."""
        clean = raw.strip()
        if clean.startswith("```"):
            parts = clean.split("```")
            if len(parts) >= 2:
                clean = parts[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # fallback: find first { and last }
            start = clean.find('{')
            end = clean.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(clean[start:end + 1])
                except json.JSONDecodeError:
                    return None
            return None

    def _error_response(self, message):
        return {
            'data': {
                'acknowledgment': message,
                'needs_clarification': True,
                'clarification_questions': [],
                'error': True
            },
            'tri': None,
            'session': {}
        }

    @staticmethod
    def _load_file(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"File not found: {path}")
            return ""


# -- CLI for quick testing --
if __name__ == '__main__':
    print("SILVIA Agent - CLI Test")
    print("Type 'quit' to exit, 'reset' to clear session")
    print("-" * 40)

    agent = SilviaAgent()
    sender = "cli_test"

    while True:
        user_input = input("\nTu: ").strip()
        if user_input.lower() == 'quit':
            break
        if user_input.lower() == 'reset':
            agent.sessions.pop(sender, None)
            print("Session cleared.")
            continue
        if not user_input:
            continue

        result = agent.process(user_input, sender=sender)
        print(f"\nSILVIA:\n{agent.format_response(result)}")
