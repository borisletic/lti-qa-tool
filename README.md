# LTI Q&A Tool

Inteligentni Q&A asistent integrisan u Canvas LMS preko IMS LTI standarda. Koristi RAG arhitekturu sa lokalnim LLM-om (Ollama Mistral), ChromaDB vektorskom bazom i automatski povlači materijale iz Canvas Course Files.

## Quick start

```bash
git clone <repo>
cd lti-qa-tool/docker
cp .env.example .env   # popuni CANVAS_API_TOKEN 
docker-compose up -d
```

Sačekaj 5-10 min da se Canvas inicijalizuje, pa skini Mistral model:

```bash
docker-compose exec ollama ollama pull mistral
```

## Pristup

| Servis | URL | Login |
|---|---|---|
| Canvas | http://localhost:3000 | admin@example.com / canvasadmin123 |
| LTI Tool | http://localhost:5000 | - |
| ChromaDB | http://localhost:8001 | - |

## Canvas setup

1. **Generiši API token**: Canvas → Account → Settings → + New Access Token → kopiraj u `.env` kao `CANVAS_API_TOKEN`
2. **Upload materijale** u Course Files (PDF, DOCX, TXT, MD)
3. **Otvori Q&A asistenta** iz Canvas modula - auto-sync se pokreće prvi put

## Stack

Flask · PyLTI1p3 · Sentence Transformers · ChromaDB · Ollama (Mistral) · Apache Jena Fuseki · Docker Compose

## Licenca

MIT - projekat za predmete *Savremene obrazovne tehnologije i standardi* i *Semantički veb*, FTN Novi Sad 2026.
