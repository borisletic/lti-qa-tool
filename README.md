# LTI Q&A Tool - Quick Start Guide

**Inteligentni Q&A asistent kao IMS LTI alat sa RAG arhitekturom i OWL ontologijom**

[![Docker](https://img.shields.io/badge/Docker-Required-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## PREDUSLOVI

- **Docker Desktop** (Windows/Mac) ili Docker Engine (Linux)
- **8GB RAM** minimum
- **20GB** slobodnog prostora
- **Git** (opciono)

---

## BRZO POKRETANJE (5 koraka)

### KORAK 1: Preuzmi projekat

```bash
# Raspakuj projekat u željeni folder
cd lti-qa-tool
```

### KORAK 2: Generiši LTI ključeve

```bash
cd lti-tool/configs

# Windows (Git Bash ili WSL)
openssl genrsa -out private.key 2048
openssl rsa -in private.key -pubout -out public.key

# Linux/macOS
openssl genrsa -out private.key 2048
openssl rsa -in private.key -pubout -out public.key

cd ../..
```

### KORAK 3: Pokreni Docker stack

```bash
cd docker
docker-compose up -d
```

**Čekanje:**
- Prvi put: **10-15 minuta** (download Ollama model + Canvas inicijalizacija)
- Svaki sledeći put: **30 sekundi**

Prati progress:
```bash
docker-compose logs -f lti_tool
```

### KORAK 4: Pristup sistemima

| Servis | URL | Kredensiali |
|--------|-----|-------------|
| **Canvas LMS** | http://localhost:3000 | admin@example.com / canvasadmin123 |
| **LTI Q&A Tool** | http://localhost:5000 | (access via Canvas) |
| **Fuseki SPARQL** | http://localhost:3030 | (no auth) |
| **ChromaDB** | http://localhost:8001 | (no auth) |

### KORAK 5: Konfiguriši LTI u Canvas-u

#### 5.1 Kreiraj Developer Key (Rails console)

```bash
docker-compose exec canvas bundle exec rails console
```

U Rails konzoli, izvršite:

```ruby
key = DeveloperKey.create!(
  name: 'Q&A Inteligentni Asistent',
  email: 'admin@example.com',
  redirect_uris: ['http://host.docker.internal:5000/launch'],
  public_jwk: {
    'kty' => 'RSA',
    'kid' => 'lti-qa-tool-key-1',
    'e' => 'AQAB',
    'n' => 'vqe12rUfkPxEKzIRyM5Nk8d8IEtTe9zSybP2nO-CrWPZAUKf9l4OstgTjRH9XvYXUHOApI-wzMoOHCPus2a-h4G3CdkPw2GxhmE-xWlMzJ82q2B_bZbQ_V5A3_KELEHUVEenH2cBdJSQGJC8RnCzd_qhOMIzITBI0SYSe5oIuZAjYiIQCYXql8bhIsK92PV-gfaLTzfWH9uXCYLPEkBN7X2ECfIJgilGtLezJ_-J7qmrbDJpnBgpWCEUqkDRpbak3iuI29NkYrmVOozVmO7HQmvYy71C4XV6j2-sxeknSWqIPIquoX9tun_Tm_dVooQexEBUmf428uO5qbVRoEJHHQ',
    'alg' => 'RS256',
    'use' => 'sig'
  },
  scopes: []
)

puts "✓ Developer Key kreiran!"
puts "Client ID: #{key.global_id}"

key.update!(workflow_state: 'active')

account = Account.find_by(name: 'FTN Test Institution') || Account.default
key.developer_key_account_bindings.create!(account: account, workflow_state: 'on')

puts "✓ Key aktiviran!"

exit
```

**VAŽNO: KOPIRAJ Client ID!** (npr. `10000000000006`)

#### 5.2 Ažuriraj LTI config

Otvori `lti-tool/configs/lti-config.json` i zameni `client_id`:

```json
{
  "http://localhost:3000": {
    "client_id": "TVOJ_CLIENT_ID_OVDE",
    "auth_login_url": "http://localhost:3000/api/lti/authorize_redirect",
    "auth_token_url": "http://localhost:3000/login/oauth2/token",
    ...
  }
}
```

**Restart LTI tool:**
```bash
docker-compose restart lti_tool
```

#### 5.3 Kreiraj kurs i dodaj tool (Rails console)

```bash
docker-compose exec canvas bundle exec rails console
```

```ruby
account = Account.find_by(name: 'FTN Test Institution') || Account.default

# Kreiraj kurs
course = Course.create!(
  name: 'Savremene obrazovne tehnologije',
  account: account,
  workflow_state: 'available'
)

puts "✓ Kurs kreiran! ID: #{course.id}"

# Dodaj External Tool
tool = ContextExternalTool.create!(
  context: course,
  name: 'Q&A Asistent',
  consumer_key: 'TVOJ_CLIENT_ID',  # Zameni sa pravim Client ID
  shared_secret: 'not_used',
  url: 'http://host.docker.internal:5000/launch',
  workflow_state: 'public',
  course_navigation: {
    text: 'Q&A Asistent',
    enabled: true
  }
)

puts "✓ External Tool dodat!"
puts "Kurs URL: http://localhost:3000/courses/#{course.id}"

# Enrolluj admina
cc = CommunicationChannel.find_by(path: 'admin@example.com')
admin = cc.user if cc
if admin
  course.enroll_user(admin, 'TeacherEnrollment', {
    enrollment_state: 'active'
  })
  puts "✓ Admin enrollovan!"
end

exit
```

---

## UPLOAD MATERIJALA

### Metod 1: Kroz UI (najlakše)

1. Login u Canvas: http://localhost:3000
2. Otvori kurs: **Savremene obrazovne tehnologije**
3. Klikni: **Q&A Asistent** u navigaciji kursa
4. Vidi **Upload nastavnih materijala"** widget
5. **Drag & drop** ili klikni za upload fajlova
6. Podržani formati: **TXT, MD, PDF, DOCX** (max 10MB)
7. Sačekaj 30-60s za procesiranje

### Metod 2: Direktno u Docker (za batch upload)

```bash
# Kopiraj materijale u container
docker cp materijali/ lti-qa-tool:/tmp/course-materials

# Upload skripta
docker-compose exec lti_tool python3 << 'EOF'
import sys
sys.path.insert(0, '/app')
from pathlib import Path
from rag_engine import get_rag_engine

rag = get_rag_engine('1')  # Course ID
materials_path = Path('/tmp/course-materials')

for file in materials_path.glob('*.txt'):
    with open(file, 'r', encoding='utf-8') as f:
        text = f.read()
    rag.add_document(text, {'filename': file.name, 'course_id': '1'})
    print(f"✓ {file.name}")

print(f"\n Upload završen!")
print(f"Statistika: {rag.get_collection_stats()}")
EOF
```

---

## UPLOAD ONTOLOGIJE U FUSEKI

```bash
docker-compose exec lti_tool python3 << 'EOF'
from rdflib import Graph
import requests

print('📚 Učitavanje ontologije...')
g = Graph()
g.parse('/app/ontology/lms-tools.ttl', format='turtle')
print(f'   ✓ Učitano {len(g)} triples')

print('\n Upload u Fuseki...')
triples = list(g)
chunk_size = 50

for i in range(0, len(triples), chunk_size):
    chunk = triples[i:i+chunk_size]
    insert_triples = [f'{s.n3()} {p.n3()} {o.n3()} .' for s, p, o in chunk]
    query = 'INSERT DATA { ' + ' '.join(insert_triples) + ' }'
    
    resp = requests.post(
        'http://fuseki:3030/lms-tools/update',
        data={'update': query},
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    if resp.status_code < 400:
        print(f'   ✓ Chunk {i//chunk_size + 1}/{len(triples)//chunk_size + 1}')
    else:
        print(f'   ✗ Error: {resp.status_code}')
        break

# Verifikuj
query_resp = requests.post(
    'http://fuseki:3030/lms-tools/query',
    data={'query': 'SELECT (COUNT(*) as ?c) WHERE {?s ?p ?o}'}
)
count = query_resp.json()['results']['bindings'][0]['c']['value']

print(f'\n Upload complete: {count} triples u Fuseki bazi')
EOF
```

**Verifikuj**: http://localhost:3030

---

## TESTIRANJE

### Test 1: Health check

```bash
curl http://localhost:5000/health
```

**Očekivano:**
```json
{"status":"healthy","service":"LTI Q&A Tool","timestamp":"2026-02-07T00:00:00.000000"}
```

### Test 2: Q&A funkcionalnost

1. Otvori Canvas → Q&A Asistent
2. Postavi pitanje: **"Šta je IMS LTI standard?"**
3. **Očekivani odgovor**: Detaljan opis LTI-ja sa confidence 65-85%

**Primer output:**
```
IMS Learning Tools Interoperability (LTI) je standard koji omogućava 
integraciju eksternih obrazovnih aplikacija u Learning Management Systems. 
LTI koristi Provider-Consumer model sa OAuth autentifikacijom...

Poverenje: 75%
Izvori: 3 chunk-a iz materijala
```

### Test 3: Pregled materijala

U Q&A Asistent UI-ju, klikni: **Pregled materijala u bazi**

**Očekivano:**
```
Statistika
Ukupno fajlova: 3
Ukupno chunks: 11

✓ canvas-lms-pregled.txt (3 chunks)
✓ lti-detaljan-vodic.txt (4 chunks)
✓ rag-arhitektura.txt (4 chunks)
```

### Test 4: SPARQL upiti

Fuseki web interface: http://localhost:3030

Klikni: **lms-tools** → **Query**

```sparql
PREFIX lms: <http://example.org/lms-tools#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class ?label WHERE {
  ?class rdf:type owl:Class .
  OPTIONAL { ?class rdfs:label ?label FILTER(lang(?label) = "en") }
}
ORDER BY ?label
LIMIT 10
```

**Očekivano**: Lista OWL klasa (LMSTool, QATool, Course, Student, ...)

---

## TROUBLESHOOTING

### Canvas se ne pokreće

```bash
# Proveri logove
docker-compose logs canvas --tail=50

# Restart
docker-compose restart canvas

# Ako i dalje ne radi, full reset:
docker-compose down
docker-compose up -d
```

### LTI tool ne radi

```bash
# Proveri logove
docker-compose logs lti_tool --tail=50

# Restart
docker-compose restart lti_tool

# Proveri health
curl http://localhost:5000/health
```

### "ChromaDB connection error"

**Ovo je normalno!** To je samo warning - sistem koristi PersistentClient umesto HttpClient. Ne utiče na funkcionalnost.

### "Worker timeout" greška

Povećaj timeout u `lti-tool/Dockerfile`:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "600", "--graceful-timeout", "600", "app:app"]
```

Rebuild:
```bash
docker-compose build lti_tool
docker-compose up -d
```

### Upload traje predugo

**Normalno za velike PDF-ove!** Očekivano vreme:
- TXT 10KB: 5s
- PDF 1MB: 30-60s
- DOCX 500KB: 20-40s

Ako upload fail-uje, proveri:
```bash
docker-compose logs lti_tool --tail=100
```

### Nema odgovora na pitanja

**Debug checklist:**
1. Proveri da su materijali upload-ovani: **📚 Pregled materijala**
2. Proveri Ollama: `docker-compose ps ollama`
3. Proveri ChromaDB: `docker-compose ps chroma`
4. Proveri logove: `docker-compose logs lti_tool --tail=50`

---

## ARHITEKTURA

```
┌─────────────────────────────────────────────────────────────┐
│                      Canvas LMS                              │
│                    (LTI Consumer)                            │
└────────────────────┬────────────────────────────────────────┘
                     │ LTI 1.1 Launch
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   LTI Q&A Tool Provider                      │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Flask App    │→ │ RAG Engine   │→ │ Ollama LLM      │   │
│  │ (LTI Logic)  │  │ (Retrieval)  │  │ (Generation)    │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
│         ↓                  ↓                                 │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Semantic     │  │ Session Mgmt │                         │
│  │ Layer (RDF)  │  │ (Flask)      │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────┬───────────────────┬───────────────────┬───────────┘
          │                   │                   │
          ↓                   ↓                   ↓
    ┌──────────┐      ┌─────────────┐     ┌──────────────┐
    │ ChromaDB │      │ Apache Jena │     │    Ollama    │
    │ Vectors  │      │   Fuseki    │     │   Mistral    │
    └──────────┘      │  (SPARQL)   │     └──────────────┘
                      └─────────────┘
```

### Tech Stack

| Komponenta | Tehnologija | Verzija |
|------------|-------------|---------|
| **Web Framework** | Flask | 3.0 |
| **LLM** | Ollama Mistral | latest (4.4GB) |
| **Embeddings** | Sentence Transformers | 2.2 (multilingual) |
| **Vector DB** | ChromaDB | 0.4.22 |
| **SPARQL Server** | Apache Jena Fuseki | latest |
| **LMS** | Canvas LMS | stable |
| **Orchestration** | Docker Compose | v2 |
| **Database** | PostgreSQL | 11 |
| **Cache** | Redis | 7 |

---

## STRUKTURA PROJEKTA

```
lti-qa-tool/
├── docker/
│   ├── docker-compose.yml          # Orchestration
│   ├── canvas-config/              # Canvas configuration
│   └── canvas-patches/             # Migration fixes
├── lti-tool/
│   ├── app.py                      # Flask application
│   ├── rag_engine.py               # RAG implementation
│   ├── semantic_layer.py           # RDF/OWL logic
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile
│   ├── configs/
│   │   ├── lti-config.json        # LTI configuration
│   │   ├── private.key            # RSA private key
│   │   └── public.key             # RSA public key
│   └── templates/
│       └── qa_interface.html      # Web UI
├── ontology/
│   └── lms-tools.ttl              # OWL ontology (304 triples)
├── scripts/
│   ├── upload_materials.py        # Upload course materials
│   └── init_ontology.py           # Initialize ontology
└── README.md
```

---

## ČIŠĆENJE

### Zaustavi sve servise

```bash
docker-compose down
```

### Obriši SAMO materijale (ne Canvas)

```bash
docker volume rm docker_chroma_data
```

### Obriši SVE volume-ove (full reset)

```bash
docker-compose down -v
```

**UPOZORENJE**: Ovo briše:
- Canvas podatke (kurseve, korisnike)
- Upload-ovane materijale
- Ontologiju iz Fuseki-ja
- Ollama model (2GB re-download!)

---

## NAPOMENE

### Performanse

- **Prvi start**: 10-15 minuta (download model-a + Canvas setup)
- **Embedding model**: 2GB, kešira se u Docker volume-u
- **Ollama model**: 4.4GB, download-uje se automatski
- **Canvas inicijalizacija**: 5-10 minuta
- **Upload timeout**: 10 minuta za velike PDF-ove

### Persistence

- **ChromaDB**: Materijali se čuvaju zauvek (dok ne obrišeš volume)
- **Fuseki**: Ontologija persists u `fuseki_data` volume-u
- **Canvas**: Kursevi i korisnici u `postgres_data` volume-u
- **Ollama**: Model u `ollama_data` volume-u
- **Embedding model**: U `huggingface_cache` volume-u

### Dupli upload

ChromaDB automatski detektuje duplikate po ID-u (`filename_chunkNumber`) i ignoriše ih - NEĆE kreirati duplikate!

---

## RAG PIPELINE

```
User Question
    ↓
Sentence Transformers (embedding)
    ↓
ChromaDB (vector search, top-8 chunks)
    ↓
Context Assembly (800 chars/chunk)
    ↓
Ollama Mistral (generation, temp=0.3)
    ↓
AI Answer + Confidence Score
```

**Confidence scoring:**
- Distance ≤ 0.35 → 95% (perfektan)
- Distance ≤ 0.45 → 85% (odličan)
- Distance ≤ 0.55 → 75% (vrlo dobar)
- Distance ≤ 0.65 → 65% (dobar)
- Distance ≤ 0.75 → 50% (solidan)
- Distance > 0.75 → 35% (prihvatljiv)

---

### Za predmet: Savremene obrazovne tehnologije i standardi

**Ključne tačke:**
1. **IMS LTI 1.1 integracija** - OAuth, Launch flow, Session management
2. **Canvas LMS deployment** - Docker, PostgreSQL, Redis
3. **RAG arhitektura** - Retrieval → Generation pipeline
4. **Lokalni AI** - Ollama (bez OpenAI API), besplatno, offline-capable
5. **File upload** - Drag & drop, TXT/MD/PDF/DOCX support

### Za predmet: Semantički veb

**Ključne tačke:**
1. **OWL 2 DL ontologija** - 304 triples, 17 klasa, 37 properties
2. **RDF reprezentacija** - Q&A sesije loguju se u RDF format
3. **Apache Jena Fuseki** - SPARQL endpoint, query interface
4. **Semantička integracija** - LTI + LMS domain u OWL-u
5. **SPARQL upiti** - Pretraga klasa, properties, instanci
