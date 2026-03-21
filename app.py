# app.py
# SILVIA - Flask + Twilio WhatsApp webhook
# Josue Mendes - 2024/2026
#
# Run: python app.py
# Test: curl -X POST http://localhost:5000/test -H "Content-Type: application/json" -d '{"message": "..."}'
# WhatsApp: cloudflared tunnel --url http://localhost:5000

import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from twilio.rest import Client as TwilioClient

from silvia_agent import SilviaAgent

load_dotenv()

TWILIO_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
CHAR_LIMIT = 800  # sandbox is picky with long messages

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('silvia.app')

app = Flask(__name__)
agent = SilviaAgent()

# twilio client for sending responses
twilio_client = None
if TWILIO_SID and TWILIO_TOKEN:
    twilio_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
    logger.info("Twilio client ready")
else:
    logger.warning("Twilio credentials missing - local-only mode")


# -- WhatsApp webhook --

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.form.get('Body', '').strip()
    sender = request.form.get('From', 'unknown')
    num_media = int(request.form.get('NumMedia', 0))

    # location if shared
    lat = request.form.get('Latitude')
    lng = request.form.get('Longitude')

    logger.info(f"Message from {sender}: {incoming_msg[:80]}...")

    if lat and lng:
        incoming_msg += f"\n[Ubicacion: {lat}, {lng}]"

    # image handling (placeholder for vision api)
    if num_media > 0:
        media_type = request.form.get('MediaContentType0', '')
        incoming_msg += f"\n[Imagen: {media_type}]"

    if not incoming_msg:
        _send_whatsapp(sender, "SILVIA esta escuchando. Envia tu observacion territorial.")
        return '', 200

    # process through agent
    try:
        result = agent.process(incoming_msg, sender=sender)
        response_text = agent.format_response(result)
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        response_text = "SILVIA encontro un error. Intenta de nuevo."

    # truncate for whatsapp
    if len(response_text) > CHAR_LIMIT:
        response_text = response_text[:CHAR_LIMIT - 20] + "\n\n[...]"
        logger.warning("Response truncated to WhatsApp limit")

    _send_whatsapp(sender, response_text)
    return '', 200


def _send_whatsapp(to, body):
    """Send via Twilio REST API (more reliable than TwiML for sandbox)."""
    if not twilio_client:
        logger.warning("No Twilio client - can't send")
        return
    try:
        twilio_client.messages.create(body=body, from_=TWILIO_NUMBER, to=to)
        logger.info(f"Response sent to {to}: {body[:80]}...")
    except Exception as e:
        logger.error(f"Twilio send error: {e}", exc_info=True)


# -- test endpoint (no twilio needed) --

@app.route('/test', methods=['POST'])
def test_endpoint():
    data = request.get_json(silent=True)
    if not data or 'message' not in data:
        return jsonify({'error': 'Send {"message": "your text"}'}), 400

    message = data['message']
    sender = data.get('sender', 'test_user')

    try:
        result = agent.process(message, sender=sender)
        formatted = agent.format_response(result)
        return jsonify({
            'formatted': formatted,
            'raw': result['data'],
            'tri': result['tri'],
            'session': result.get('session', {})
        })
    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# -- health + debug --

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'SILVIA',
        'version': '0.1.0',
        'sessions': len(agent.sessions),
        'twilio': twilio_client is not None
    })


@app.route('/session/<sender>', methods=['GET'])
def session_info(sender):
    if not DEBUG:
        return jsonify({'error': 'debug mode off'}), 403
    session = agent.sessions.get(sender)
    if not session:
        return jsonify({'error': 'not found'}), 404
    return jsonify({
        'community': session['community_module'],
        'observer_role': session['observer_role'],
        'observations': session['observation_count'],
        'history_len': len(session['history'])
    })


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("SILVIA v0.1.0")
    logger.info(f"Port: {PORT} | Debug: {DEBUG}")
    logger.info(f"Twilio: {'connected' if twilio_client else 'local-only'}")
    logger.info("")
    logger.info("Endpoints:")
    logger.info(f"  WhatsApp webhook:  POST http://localhost:{PORT}/webhook")
    logger.info(f"  Direct test:       POST http://localhost:{PORT}/test")
    logger.info(f"  Health check:      GET  http://localhost:{PORT}/health")
    logger.info("")
    logger.info("To connect WhatsApp:")
    logger.info("  1. cloudflared tunnel --url http://localhost:5000")
    logger.info("  2. Copy URL to Twilio Sandbox settings")
    logger.info("  3. Webhook: https://<tunnel-id>.trycloudflare.com/webhook")
    logger.info("=" * 50)

    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
