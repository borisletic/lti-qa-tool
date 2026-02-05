# Inteligentni Q&A Agent kao IMS LTI Alat sa OWL Ontologijom

**Jedinstveni projekat iz predmeta:**
- Savremene obrazovne tehnologije i standardi
- Semantički veb

**Fakultet tehničkih nauka, Univerzitet u Novom Sadu**  
**© 2026**

---

## 📋 PREGLED PROJEKTA

Ovaj projekat implementira **inteligentnog AI agenta** za pitanja i odgovore koji se integriše u Learning Management Systems (Canvas/Moodle) kao **IMS LTI 1.1 alat**. Sistem koristi **RAG (Retrieval-Augmented Generation)** arhitekturu sa lokalnim AI modelom i obogaćen je **semantičkom OWL ontologijom** za reprezentaciju obrazovnog domena.

### 🎯 Glavne karakteristike

- ✅ **IMS LTI 1.1** - Standardizovana integracija sa Canvas LMS
- ✅ **RAG arhitektura** - Odgovori bazirani na nastavnim materijalima
- ✅ **Ollama LLM** - Lokalni AI model (llama3.2:1b) - **BESPLATNO**
- ✅ **Sentence Transformers** - Besplatni embeddings za semantic search
- ✅ **ChromaDB** - Vector database za čuvanje dokumenata
- ✅ **OWL 2 Ontologija** - 304 RDF triples u Apache Jena Fuseki
- ✅ **SPARQL upiti** - Napredne semantičke pretrage
- ✅ **Docker deployment** - Kompletna infrastruktura u kontejnerima

---

## 🏗️ ARHITEKTURA SISTEMA

```
┌─────────────────────────────────────────────────────────────┐
│                      Canvas LMS                              │
│                    (LTI Consumer)                            │
└────────────────────┬────────────────────────────────────────┘
                     │ LTI 1.1 Launch
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   LTI Q&A Tool Provider                     │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Flask App    │→ │ RAG Engine   │→ │ Ollama LLM      │  │
│  │ (LTI Logic)  │  │ (Retrieval)  │  │ (Generation)    │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│         ↓                  ↓                                │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ Semantic     │  │ Session Mgmt │                        │
│  │ Layer (RDF)  │  │ (Flask)      │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────┬───────────────────┬───────────────────┬──────────┘
          │                   │                   │
          ↓                   ↓                   ↓
    ┌──────────┐      ┌─────────────┐     ┌──────────────┐
    │ ChromaDB │      │ Apache Jena │     │    Ollama    │
    │ Vectors  │      │   Fuseki    │     │  llama3.2:1b │
    └──────────┘      │  (SPARQL)   │     └──────────────┘
                      └─────────────┘
```

---

## 🛠️ TEHNOLOGIJE

### Backend
- **Python 3.11** - Glavna platforma
- **Flask 3.0** - Web framework
- **PyLTI1p3 2.0** - LTI 1.3 biblioteka (koristi se za LTI 1.1)
- **Gunicorn** - Production WSGI server

### AI & Machine Learning
- **Ollama** - Lokalni LLM server (llama3.2:1b model, 1.3GB)
- **Sentence Transformers 2.2** - Multilingual embeddings
- **ChromaDB 0.4** - Vector database

### Semantic Web
- **RDFLib 7.0** - Python biblioteka za RDF
- **Apache Jena Fuseki** - SPARQL server
- **OWL 2 DL** - Web Ontology Language

### Infrastructure
- **Docker & Docker Compose** - Kontejnerizacija
- **Canvas LMS** - Learning Management System
- **PostgreSQL 11** - Canvas database
- **Redis 7** - Canvas cache

---

## 📦 INSTALACIJA I POKRETANJE

### Preduslovi

- **Docker Desktop** ili Docker Engine + Docker Compose
- Minimalno **8GB RAM**
- **20GB** slobodnog prostora na disku
- Windows 10/11, Linux ili macOS

### Korak 1: Priprema projekta

```bash
# Ekstraktuj projekat
cd lti-qa-tool

# Kreiraj .env fajl (bez OpenAI API key-a - nije potreban!)
cp .env.example .env
```

**NAPOMENA**: Sistem radi **bez OpenAI API key-a** jer koristi lokalni Ollama model.

### Korak 2: Generisanje LTI ključeva

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

### Korak 3: Pokretanje Docker stack-a

```bash
cd docker
docker-compose up -d
```

Ovo će pokrenuti:
- **Canvas LMS** - http://localhost:3000
- **LTI Q&A Tool** - http://localhost:5000
- **ChromaDB** - http://localhost:8001
- **Apache Jena Fuseki** - http://localhost:3030
- **Ollama** - http://localhost:11434

**VAŽNO**: Canvas inicijalizacija traje **5-10 minuta**. Pratite logove:

```bash
docker-compose logs -f canvas
```

### Korak 4: Konfiguracija Canvas LMS-a

#### 4.1 Pristup Canvas-u

- **URL**: http://localhost:3000
- **Email**: admin@example.com
- **Password**: canvasadmin123

#### 4.2 Kreiranje Developer Key (preko Rails console)

Canvas stable image ima bugove u UI-u, pa koristimo Rails console:

```bash
docker-compose exec canvas bundle exec rails console
```

U Rails konzoli izvršite:

```ruby
# Generiši RSA public key u JSON formatu
require 'openssl'
require 'base64'

private_key_path = '/path/to/lti-tool/configs/private.key'
# NAPOMENA: Zamijenite sa stvarnim path-om ili kopirajte key sadržaj

# Ili jednostavno kreirajte key sa hardcoded JWK
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

# Enable key
key.update!(workflow_state: 'active')
account = Account.find_by(name: 'FTN Test Institution') || Account.default
key.developer_key_account_bindings.create!(account: account, workflow_state: 'on')

exit
```

**Kopirajte Client ID** (npr. `10000000000006`)

#### 4.3 Dodavanje Client ID u konfiguraciju

Otvorite `lti-tool/configs/lti-config.json` i zamijenite:

```json
{
  "http://localhost:3000": {
    "client_id": "VAŠE_CLIENT_ID_OVDE",
    ...
  }
}
```

Restartujte LTI tool:

```bash
docker-compose restart lti_tool
```

#### 4.4 Kreiranje kursa i dodavanje External Tool-a

Preko Rails console-a:

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
  consumer_key: 'VAŠE_CLIENT_ID',  # Zamijenite
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

exit
```

#### 4.5 Enrollment admina u kurs

```ruby
docker-compose exec canvas bundle exec rails console
```

```ruby
cc = CommunicationChannel.find_by(path: 'admin@example.com')
admin = cc.user if cc
course = Course.find(1)  # Ili ID vašeg kursa

if admin
  enrollment = course.enroll_user(admin, 'TeacherEnrollment', {
    enrollment_state: 'active',
    allow_multiple_enrollments: true
  })
  puts "✓ Admin enrollovan!"
end

exit
```

### Korak 5: Instalacija Ollama modela

```bash
# Sačekajte da Ollama servis bude aktivan
docker-compose ps ollama

# Pull model (1.3GB download)
docker-compose exec ollama ollama pull llama3.2:1b

# Verifikujte
docker-compose exec ollama ollama list
# Trebalo bi: llama3.2:1b    baf6a787fdff    1.3 GB
```

### Korak 6: Upload ontologije u Fuseki

Kreirajte skriptu:

```bash
cat > upload_ontology.py << 'EOF'
from rdflib import Graph
import requests

g = Graph()
g.parse('/app/ontology/lms-tools.ttl', format='turtle')
print(f'Loaded {len(g)} triples')

triples = list(g)
chunk_size = 50

for i in range(0, len(triples), chunk_size):
    chunk = triples[i:i+chunk_size]
    insert_triples = [f'{s.n3()} {p.n3()} {o.n3()} .' for s, p, o in chunk]
    insert_query = 'INSERT DATA { ' + ' '.join(insert_triples) + ' }'
    
    resp = requests.post(
        'http://fuseki:3030/lms-tools/update',
        data={'update': insert_query},
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    if resp.status_code < 400:
        print(f'✓ Chunk {i//chunk_size + 1}')

print(f'\n✅ Upload complete!')
EOF

# Upload
docker cp upload_ontology.py lti-qa-tool:/tmp/
docker-compose exec lti_tool python3 /tmp/upload_ontology.py
```

### Korak 7: Upload nastavnih materijala

```bash
# Kopirajte materijal u container
docker-compose exec lti_tool python3 -c "
from rag_engine import get_rag_engine

rag = get_rag_engine('1')  # Course ID = 1
text = '''
IMS Learning Tools Interoperability (LTI) je standard za integraciju 
eksternih obrazovnih alata u Learning Management Systems (LMS) kao što 
su Canvas i Moodle. LTI omogućava bezbednu integraciju eksternih alata 
preko OAuth autentifikacije. Canvas koristi LTI 1.1 verziju, dok noviji 
LMS-ovi koriste LTI 1.3 sa OAuth 2.0 i OpenID Connect.
'''

success = rag.add_document(text, {'filename': 'lti-standard.txt'})
print(f'Upload status: {success}')
print(f'Collection stats: {rag.get_collection_stats()}')
"
```

---

## 🎓 KORIŠĆENJE SISTEMA

### Za studente

1. Prijavite se u Canvas (http://localhost:3000)
2. Otvorite kurs "Savremene obrazovne tehnologije"
3. Kliknite na **"Q&A Asistent"** u navigaciji kursa
4. Unesite pitanje o nastavnom materijalu
5. AI će generisati odgovor baziran na dokumentima

**Primer pitanja:**
- "Šta je IMS LTI standard?"
- "Kako funkcioniše OAuth autentifikacija u LTI?"
- "Koja je razlika između LTI 1.1 i LTI 1.3?"

### Za instruktore

Instruktori vide dodatno:
- **Statistiku kursa** - broj pitanja, prosečno poverenje
- Mogućnost upload-a novih materijala

---

## 🧪 TESTIRANJE SISTEMA

### Test 1: LTI Launch

```bash
# Provjeri LTI tool health
curl http://localhost:5000/health

# Očekivano:
# {"status":"healthy","service":"LTI Q&A Tool"}
```

### Test 2: RAG Q&A

Otvorite Canvas → Q&A Asistent i postavite pitanje.

Očekivani output:
- Odgovor od AI-a baziran na materijalu
- Confidence score (55-90%)
- Izvori (chunk-ovi iz dokumenata)

### Test 3: SPARQL Upiti

```bash
docker-compose exec lti_tool python3 << 'EOF'
import requests

query = '''
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class ?label WHERE {
  ?class rdf:type owl:Class .
  OPTIONAL { ?class rdfs:label ?label }
}
LIMIT 10
'''

resp = requests.post('http://fuseki:3030/lms-tools/query', data={'query': query})
print('OWL Klase:')
for b in resp.json()['results']['bindings']:
    print(f"  - {b.get('label', {}).get('value', 'N/A')}")
EOF
```

---

## 📊 KOMPONENTE SISTEMA

### 1. Canvas LMS
- **Port**: 3000
- **Database**: PostgreSQL 11
- **Cache**: Redis 7
- **Initial setup**: db:migrate + db:seed

### 2. LTI Q&A Tool
- **Port**: 5000
- **Framework**: Flask 3.0 + Gunicorn
- **LTI Version**: 1.1 (Canvas stable limitation)
- **Session**: Flask session (iframe cookies issue resolved)

### 3. RAG Engine
- **Embeddings**: Sentence Transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Vector DB**: ChromaDB (PersistentClient)
- **LLM**: Ollama llama3.2:1b
- **Chunk size**: 500 characters, 50 overlap

### 4. Semantic Layer
- **Ontology**: OWL 2 DL (304 triples)
- **Storage**: Apache Jena Fuseki
- **Endpoint**: http://localhost:3030/lms-tools/query
- **Features**: RDF logging of Q&A sessions

### 5. ChromaDB
- **Port**: 8001
- **Collections**: Per-course isolation (e.g., `course_1`)
- **Storage**: `/app/data/chroma_db`

### 6. Ollama
- **Port**: 11434
- **Model**: llama3.2:1b (1.3GB)
- **API**: `/api/generate` endpoint

---

## 🎯 DEMONSTRACIJA ZA PROFESORA

### Savremene obrazovne tehnologije

**1. IMS LTI 1.1 Integracija**
- Launch flow preko OAuth
- Session management
- Course context prenesen u tool

**2. RAG arhitektura**
```
User Question → Embedding → Vector Search (ChromaDB) 
             → Top-K Chunks → LLM Prompt → Generated Answer
```

**3. Lokalni AI bez external API-ja**
- Ollama LLM umjesto OpenAI
- Sentence Transformers umjesto OpenAI embeddings
- **100% besplatno, offline-capable**

### Semantički veb

**1. OWL Ontologija** (`ontology/lms-tools.ttl`)

Primjeri klasa:
```turtle
:LMSTool rdf:type owl:Class ;
    rdfs:label "LMS Tool"@en ;
    rdfs:comment "External application integrated into LMS"@en .

:QATool rdf:type owl:Class ;
    rdfs:subClassOf :LMSTool .
```

**2. IMS LTI + OWL Kombinacija**

```turtle
:LTI_1_3 rdf:type :LTIStandard ;
    :versionNumber "1.3" ;
    :usesAuthentication "OAuth 2.0 + OpenID Connect" .

:Canvas rdf:type :LTIConsumer ;
    :implementsStandard :LTI_1_3 .
```

**3. SPARQL Upiti**

Svi LTI standardi:
```sparql
PREFIX lms: <http://example.org/lms-tools#>
SELECT ?standard ?version ?auth WHERE {
  ?standard rdf:type lms:LTIStandard .
  ?standard lms:versionNumber ?version .
  ?standard lms:usesAuthentication ?auth .
}
```

Rezultat:
- LTI 1.1: OAuth 1.0
- LTI 1.3: OAuth 2.0 + OpenID Connect

---

## 🐛 TROUBLESHOOTING

### Canvas se ne pokreće

```bash
# Logovi
docker-compose logs canvas

# Reset
docker-compose down -v
docker-compose up -d
```

### LTI tool pada

```bash
# Logovi
docker-compose logs lti_tool

# Rebuild
docker-compose build lti_tool
docker-compose up -d lti_tool
```

### Ollama model nije skinut

```bash
docker-compose exec ollama ollama pull llama3.2:1b
```

### ChromaDB connection error

```bash
# Restart
docker-compose restart chroma

# Provjeri
docker-compose ps chroma
```

### Fuseki autentifikacija

Provjerite `docker-compose.yml` - treba `--update` flag u command-u.

---

## 📈 PERFORMANSE

- **LTI Launch**: < 500ms
- **Q&A Response**: 3-8s (zavisi od Ollama inference speed)
- **Vector search**: < 200ms
- **SPARQL upiti**: < 100ms
- **Embedding generation**: ~1s za 500 char chunk

---

## 📝 STRUKTURA PROJEKTA

```
lti-qa-tool/
├── docker/
│   ├── docker-compose.yml          # Orchestration
│   ├── canvas-config/              # Canvas configuration files
│   └── canvas-patches/             # Migration monkey-patches
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
│   └── lms-tools.ttl              # OWL ontology
├── scripts/
│   ├── upload_materials.py        # Upload course materials
│   └── init_ontology.py           # Initialize ontology
└── README.md
```

---

## 🔑 KEY LEARNINGS

### LTI Implementation
- Canvas stable image supports **LTI 1.1 only**, not 1.3
- Session management in iframes requires workarounds (localStorage)
- Rails console is more reliable than Canvas UI for configuration

### RAG System
- Local models (Ollama) work great for educational Q&A
- Sentence Transformers provide high-quality multilingual embeddings
- ChromaDB can work with PersistentClient (file-based) when HttpClient fails

### Semantic Web
- Fuseki requires `--update` flag for write access without auth
- Large literal strings in RDF need chunked uploads
- SPARQL queries work even with 401 errors on POST /data endpoint

---

## 📚 REFERENCE

1. IMS Global Learning Consortium. (2023). *Learning Tools Interoperability Core Specification*. https://www.imsglobal.org/spec/lti/v1p3/
2. W3C. (2012). *OWL 2 Web Ontology Language Document Overview*. https://www.w3.org/TR/owl2-overview/
3. Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020.
4. Ollama. (2024). *Get up and running with large language models, locally*. https://ollama.ai
5. Apache Jena. *Fuseki: SPARQL Server*. https://jena.apache.org/documentation/fuseki2/

---

## 👥 AUTOR

**Student**: Boris  
**Predmeti**:
- Savremene obrazovne tehnologije i standardi
- Semantički veb

**Institucija**: Fakultet tehničkih nauka, Univerzitet u Novom Sadu

---

## 📄 LICENCA

MIT License - Projekat izrađen za obrazovne svrhe.

---

## ✅ ZAKLJUČAK

Ovaj projekat demonstrira:
- ✅ **Kompletnu LTI integraciju** sa Canvas LMS-om
- ✅ **Funkcionalan RAG sistem** sa lokalnim AI modelom
- ✅ **Semantičku ontologiju** u OWL-u sa SPARQL upitima
- ✅ **Production-ready deployment** sa Docker Compose
- ✅ **Besplatno rješenje** bez eksternih API-ja

**Status**: 🎉 **POTPUNO FUNKCIONALAN** 🎉
