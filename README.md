# Inteligentni Q&A Agent kao IMS LTI Alat sa Semantičkom Ontologijom

Jedinstveni projekat iz predmeta **Savremene obrazovne tehnologije i standardi** i **Semantički veb**  
Fakultet tehničkih nauka, Univerzitet u Novom Sadu

## 📋 Pregled projekta

Ovaj projekat implementira inteligentnog agenta za pitanja i odgovore koji se integriše u Learning Management Systems (Canvas/Moodle) kao IMS LTI 1.3 alat. Sistem koristi RAG (Retrieval-Augmented Generation) arhitekturu i obogaćen je semantičkom ontologijom izrađenom u OWL-u.

### Glavne karakteristike

- ✅ **IMS LTI 1.3 Advantage** - Standardizovana integracija sa LMS platformama
- ✅ **AI-powered Q&A** - GPT-4 baziran sistem za odgovaranje na pitanja
- ✅ **RAG arhitektura** - Pretraga relevantnog sadržaja iz nastavnih materijala
- ✅ **OWL Ontologija** - Semantička reprezentacija LMS alata i obrazovnog konteksta
- ✅ **SPARQL upiti** - Napredne semantičke pretrage
- ✅ **Docker deployment** - Kompletna infrastruktura u kontejnerima

## 🏗️ Arhitektura

```
┌─────────────────────────────────────────────────────────────┐
│                      Canvas/Moodle LMS                      │
│                    (LTI Tool Consumer)                      │
└────────────────────┬────────────────────────────────────────┘
                     │ LTI 1.3 Launch
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   LTI Q&A Tool Provider                     │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Flask App    │  │ Semantic     │  │ AI Q&A Engine   │  │
│  │ (LTI Logic)  │→ │ Layer (RDF)  │→ │ (LangChain)     │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────┬───────────────────┬───────────────────┬──────────┘
          │                   │                   │
          ↓                   ↓                   ↓
    ┌──────────┐      ┌─────────────┐     ┌──────────────┐
    │ ChromaDB │      │ Apache Jena │     │  OpenAI API  │
    │ (Vectors)│      │   Fuseki    │     │   (GPT-4)    │
    └──────────┘      │  (SPARQL)   │     └──────────────┘
                      └─────────────┘
```

## 🛠️ Tehnologije

### Backend
- **Python 3.11** - Glavna platforma
- **Flask** - Web framework
- **PyLTI1.3** - LTI 1.3 implementacija
- **LangChain** - LLM framework
- **OpenAI API** - GPT-4 model

### Vector Database
- **ChromaDB** - Skladištenje i pretraga embeddings

### Semantic Web
- **RDFLib** - Python biblioteka za RDF
- **Apache Jena Fuseki** - SPARQL server
- **OWL 2** - Ontologija

### Infrastructure
- **Docker & Docker Compose** - Kontejnerizacija
- **PostgreSQL** - Baza za Canvas
- **Redis** - Cache za Canvas
- **Nginx** - Reverse proxy (opciono)

## 📦 Instalacija i pokretanje

### Preduslovi

- Docker Desktop ili Docker Engine + Docker Compose
- OpenAI API ključ
- Minimalno 8GB RAM
- 20GB slobodnog prostora na disku

### Korak 1: Kloniranje projekta

```bash
git clone https://github.com/your-username/lti-qa-tool.git
cd lti-qa-tool
```

### Korak 2: Konfiguracija environment varijabli

Kreirajte `.env` fajl u root direktorijumu:

```bash
# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key-here

# Flask
FLASK_SECRET_KEY=your-random-secret-key-here

# LTI Credentials
LTI_KEY=your_lti_key
LTI_SECRET=your_lti_secret

# Database
POSTGRES_PASSWORD=canvas_pg_password
```

### Korak 3: Generisanje LTI ključeva

```bash
# Generisanje RSA key pair za LTI
cd lti-tool/configs
openssl genrsa -out private.key 2048
openssl rsa -in private.key -pubout -out public.key
cd ../..
```

### Korak 4: Pokretanje sa Docker Compose

```bash
cd docker
docker-compose up -d
```

Ovo će pokrenuti sledeće servise:
- **Canvas LMS** - http://localhost:3000
- **LTI Q&A Tool** - http://localhost:5000
- **ChromaDB** - http://localhost:8001
- **Apache Jena Fuseki** - http://localhost:3030

### Korak 5: Inicijalizacija Canvas LMS

```bash
# Pristupite Canvas admin panelu
# URL: http://localhost:3000
# Email: admin@example.com
# Password: canvasadmin123

# Pratite wizard za inicijalno podešavanje
```

### Korak 6: Konfiguracija LTI alata u Canvas-u

1. Ulogujte se kao admin u Canvas
2. Idite na **Admin** → **Developer Keys**
3. Kliknite **+ Developer Key** → **+ LTI Key**
4. Popunite podatke:
   - **Key Name**: Q&A Tool
   - **Redirect URIs**: `http://localhost:5000/launch`
   - **JWK Method**: Public JWK URL
   - **Public JWK URL**: `http://localhost:5000/jwks`
5. Sačuvajte **Client ID** i dodajte ga u `lti-config.json`

### Korak 7: Upload nastavnih materijala

```bash
# Kopirajte PDF, Word ili text fajlove u data/courses/{COURSE_ID}
python scripts/upload_materials.py --course-id COURSE_001 --files ./sample-materials/
```

## 📚 Struktura projekta

```
lti-qa-tool/
├── docker/
│   └── docker-compose.yml          # Docker orkestrator
├── lti-tool/
│   ├── app.py                      # Glavni Flask aplikacija
│   ├── semantic_layer.py           # RDF/OWL logika
│   ├── requirements.txt            # Python zavisnosti
│   ├── Dockerfile                  # Docker image
│   ├── configs/
│   │   ├── lti-config.json        # LTI konfiguracija
│   │   ├── private.key            # LTI privatni ključ
│   │   └── public.key             # LTI javni ključ
│   └── templates/
│       └── qa_interface.html      # UI interfejs
├── ontology/
│   └── lms-tools.ttl              # OWL ontologija
├── scripts/
│   ├── upload_materials.py        # Upload nastavnih materijala
│   └── init_ontology.py           # Inicijalizacija ontologije
└── README.md
```

## 🧪 Testiranje

### Unit testovi

```bash
cd lti-tool
pytest tests/
```

### Testiranje LTI launch-a

```bash
# Koristite LTI Tool Launcher za simulaciju
# https://lti-ri.imsglobal.org/lti/tools
```

### SPARQL upiti

```bash
# Pristupite Fuseki web interfejsu
# http://localhost:3030/lms-tools

# Primer upita - sve Q&A sesije za kurs
PREFIX lms: <http://example.org/lms-tools#>
SELECT ?question ?answer WHERE {
  ?q rdf:type lms:Question .
  ?q lms:relatedToCourse <http://example.org/courses/COURSE_001> .
  ?q lms:questionText ?question .
  ?ans lms:answersQuestion ?q .
  ?ans lms:answerText ?answer .
}
```

## 📖 Korišćenje

### Za studente

1. Otvorite kurs u Canvas/Moodle
2. Kliknite na "Q&A Asistent" u navigaciji kursa
3. Unesite pitanje o nastavnom materijalu
4. Dobijte AI-generisan odgovor sa izvorima

### Za instruktore

- Pregled statistike pitanja
- Upload novih materijala
- Monitoring confidence score-a

## 🎓 Obrazovni aspekti

### Savremene obrazovne tehnologije i standardi

- Implementacija IMS LTI 1.3 Advantage standarda
- OAuth 2.0 + OpenID Connect autentifikacija
- Deep linking integracija
- Assignment and Grade Services (opciono)

### Semantički veb

- OWL 2 DL ontologija za LMS domene
- RDF triplet reprezentacija Q&A sesija
- SPARQL upiti za semantičku pretragu
- Automatsko zaključivanje sa reasoners (HermiT/Pellet)

## 🔧 Troubleshooting

### Canvas se ne pokreće

```bash
# Proverite logove
docker-compose logs canvas

# Resetujte bazu
docker-compose down -v
docker-compose up -d
```

### LTI validacija ne prolazi

- Proverite da su `private.key` i `public.key` ispravno generisani
- Verifikujte Client ID u `lti-config.json`
- Proverite JWKS endpoint: http://localhost:5000/jwks

### ChromaDB greška

```bash
# Resetujte vector database
rm -rf data/courses/*
python scripts/upload_materials.py --course-id COURSE_001 --files ./materials/
```

## 📊 Performanse

- **LTI Launch**: < 500ms
- **Q&A Response**: 2-5s (zavisno od kompleksnosti pitanja)
- **Vector search**: < 200ms
- **SPARQL upiti**: < 100ms

## 🚀 Production deployment

Za produkcijsko okruženje:

1. Koristite HTTPS sa SSL sertifikatima
2. Podesite Nginx reverse proxy
3. Omogućite rate limiting
4. Konfigurirajte log agregaciju
5. Implementirajte monitoring (Prometheus/Grafana)

```bash
docker-compose --profile production up -d
```

## 📝 Licenca

MIT License - Projekat izrađen za obrazovne svrhe.

## 👥 Autori

- **Student**: [Vaše ime]
- **Predmeti**: 
  - Savremene obrazovne tehnologije i standardi
  - Semantički veb
- **Institucija**: Fakultet tehničkih nauka, Univerzitet u Novom Sadu

## 📚 Reference

1. IMS Global Learning Consortium. (2023). *Learning Tools Interoperability Core Specification*. https://www.imsglobal.org/spec/lti/v1p3/
2. W3C. (2012). *OWL 2 Web Ontology Language Document Overview*. https://www.w3.org/TR/owl2-overview/
3. Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020.

## 🙏 Zahvalnice

- IMS Global Learning Consortium za LTI standard
- W3C za OWL i RDF standarde
- OpenAI za GPT-4 API
- Instructure za Canvas LMS
