# SILVIA — Sovereign Information Learning Virtual Intelligent Architecture

A federated Digital Twin framework for sovereign territorial data governance.

**Author:** Josue Mendes · Diplom-Architekt (USB/Anabin H+) · BIM Specialist  
**Contact:** josuemendesv@gmail.com  
**License:** AGPL-3.0  
**Status:** Proof of Concept + Executive Summary (v0.2.0)

---

## What is SILVIA?

SILVIA is a modular framework that converts qualitative territorial observations into structured ecological knowledge graphs. It bridges the gap between ISO 19650 digital twin standards and low-connectivity environments where communities monitor their own territories.

A community member sends a WhatsApp message describing what they observe. SILVIA identifies the community context, interprets the observation using a locally-defined knowledge base, calculates a Territorial Regeneration Index (TRI), and stores everything as linked notes in an Obsidian vault — creating a visual Digital Twin that grows with every observation.

Proof of Concept is avaible on youtube:

[![SILVIA PoC Demo](https://img.youtube.com/vi/zXmm28oHyhg/maxresdefault.jpg)](https://youtu.be/zXmm28oHyhg)



## Architecture

Three-layer stack:

**Layer 1 — SILVIA Core:** Community detection, universal TRI calculation, CARE data sovereignty principles, response formatting. Territory-agnostic.

**Layer 2 — Community Modules:** Pluggable knowledge bases per territory. Each module defines local species indicators, toponymy, seasonal patterns, and cultural practices. Currently implemented: Pemón/Kanaimö (Gran Sabana, Venezuela) and Caracas Urban.

**Layer 3 — DT Lifecycle:** Analytical capacity scales with data maturity. Shadow (no data) → Embryonic (<50 observations) → Juvenile (50-500) → Mature (500+, community-validated).

## Territorial Regeneration Index (TRI)

Composite metric grounded in Berkes (2008), Mang & Reed (2012), and Niemi & McDonald (2004):

```
TRI = (w1 × ESD) + (w2 × TCI) + (w3 × RAR_norm) + (w4 × IIS)
```

| Variable | Range | Description |
|----------|-------|-------------|
| ESD | 0–1 | Ecosystem Services Diversity |
| TCI | 0–1 | Territorial Cultural Integrity |
| RAR | -1 to 1 | Regeneration-to-Alteration Ratio |
| IIS | 0–1 | Indigenous/Inhabitant Information Sovereignty |

Default weights: ESD=0.25, TCI=0.25, RAR=0.30, IIS=0.20. Overridable per community module. These are working hypotheses pending empirical validation.

The differentiator from conventional indices: IIS quantifies data sovereignty. The same observation generates a different TRI depending on whether it comes from a community leader (IIS=1.0) or an external observer (IIS=0.3).

## Technical Stack

- **Interface:** WhatsApp (Twilio + Cloudflare Tunnel)
- **Backend:** Flask / Python 3.10+
- **Inference:** Claude API (Anthropic), structured JSON output
- **Index:** TRI engine with per-module weight configuration
- **Storage:** Obsidian vault with wikilinked markdown notes
- **Governance:** CARE principles as flags in every observation

## Project Structure

```
SILVIA/
├── app.py                    # Flask + Twilio webhook
├── silvia_agent.py           # Core agent, dynamic prompt composition
├── tri_engine.py             # TRI calculator
├── obsidian_vault.py         # Obsidian note generator
├── test_integration.py       # Integration tests (no API key needed)
├── prompts/
│   └── silvia_core.txt       # System prompt (Layer 1)
└── community_modules/
    ├── pemon_kanaimo.txt     # Pemón territory module
    └── caracas_urban.txt     # Caracas urban module
```

## Quick Start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your keys

python tri_engine.py           # unit tests
python test_integration.py     # full pipeline test (no API key)
python app.py                  # start server
```

## Academic Context

SILVIA addresses the gap identified by Petzold (2024) in "Situating Digital Participation" — the disconnect between digital twin infrastructure and the communities inhabiting modeled territories. The Obsidian knowledge graph is visual proof of the DT lifecycle: empty vault = Shadow, clustered nodes = Embryonic, dense network = Mature.

### References

- Berkes, F. (2008). *Sacred Ecology*. Routledge.
- Mang, P., & Reed, B. (2012). Designing from place. *Building Research & Information*, 40(1), 23-38.
- Niemi, G. J., & McDonald, M. E. (2004). Application of ecological indicators. *AREES*, 35, 89-111.
- Petzold, F. (2024). Situating Digital Participation. TUM.
- CARE Principles for Indigenous Data Governance. GIDA.

## License

AGPL-3.0 — derivative works must remain open source, protecting the framework as a tool for community sovereignty.

## Citation

```bibtex
@software{mendes_silvia_2026,
  author       = {Mendes, Josue},
  title        = {{SILVIA: Sovereign Information Learning Virtual Intelligent Architecture}},
  year         = 2026,
  publisher    = {Zenodo},
  version      = {v0.1.0},
  doi          = {10.5281/zenodo.19151384}
}
```

---

*Developed in Munich, Germany. Research origins: Gran Sabana, Venezuela (2022-2023).*
