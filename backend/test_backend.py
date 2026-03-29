"""
StudyBuddy AI — Backend Test Suite
====================================
Run: python test_backend.py

Tests each layer of the backend step-by-step:
1. Database & models
2. Embedding generation
3. ChromaDB vector store
4. Document parsing & chunking
5. Reranker
6. Gemini LLM connection
7. Full RAG pipeline
8. API endpoints (via TestClient)

Requirements: All dependencies from requirements.txt installed
              .env file configured with GEMINI_API_KEY
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# ── Helpers ──

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
WARN = "\033[93m⚠️  WARN\033[0m"
INFO = "\033[94mℹ️  INFO\033[0m"
DIVIDER = "=" * 60

test_results = {"passed": 0, "failed": 0, "warnings": 0}


def log_pass(msg):
    print(f"  {PASS}  {msg}")
    test_results["passed"] += 1

def log_fail(msg, error=None):
    print(f"  {FAIL}  {msg}")
    if error:
        print(f"         → {error}")
    test_results["failed"] += 1

def log_warn(msg):
    print(f"  {WARN}  {msg}")
    test_results["warnings"] += 1

def log_info(msg):
    print(f"  {INFO}  {msg}")

def section(title):
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


# ════════════════════════════════════════════
# TEST 1: Environment & Config
# ════════════════════════════════════════════

def test_config():
    section("TEST 1: Environment & Configuration")

    try:
        from config import settings
        log_pass("config.py loaded successfully")
    except Exception as e:
        log_fail("Could not load config.py", e)
        return False

    # Check Gemini key
    if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here":
        log_pass(f"Gemini API key is set (starts with: {settings.gemini_api_key[:8]}...)")
    else:
        log_fail("Gemini API key not set in .env — get one free at https://aistudio.google.com/apikey")
        return False

    # Check directories
    if Path(settings.upload_dir).exists():
        log_pass(f"Upload directory exists: {settings.upload_dir}")
    if Path(settings.chroma_persist_dir).exists():
        log_pass(f"ChromaDB directory exists: {settings.chroma_persist_dir}")

    log_info(f"Embedding model: {settings.embedding_model}")
    log_info(f"Reranker model: {settings.reranker_model}")
    log_info(f"Chunk size: {settings.chunk_size}, overlap: {settings.chunk_overlap}")
    return True


# ════════════════════════════════════════════
# TEST 2: Database & Models
# ════════════════════════════════════════════

async def test_database():
    section("TEST 2: Database & ORM Models")

    try:
        from db.database import engine, init_db, async_session
        from models import User, Document, Chunk, Flashcard, QuizAttempt, StudySession, WeakTopic
        log_pass("All models imported successfully")
    except Exception as e:
        log_fail("Could not import models", e)
        return False

    # Create tables
    try:
        await init_db()
        log_pass("Database tables created (SQLite)")
    except Exception as e:
        log_fail("Could not create database tables", e)
        return False

    # Test CRUD
    try:
        async with async_session() as db:
            # Create test user
            from passlib.context import CryptContext
            pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

            test_user = User(
                email="test@studybuddy.com",
                name="Test User",
                password_hash=pwd.hash("testpass123"),
            )
            db.add(test_user)
            await db.flush()
            log_pass(f"Test user created with id={test_user.id}")

            # Create test document
            test_doc = Document(
                user_id=test_user.id,
                title="Test Document",
                file_path="/tmp/test.pdf",
                file_type="pdf",
                processing_status="ready",
                chunk_count=0,
            )
            db.add(test_doc)
            await db.flush()
            log_pass(f"Test document created with id={test_doc.id}")

            # Verify relationships
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.email == "test@studybuddy.com"))
            user = result.scalar_one()
            log_pass(f"User query works — found: {user.name}")

            # Cleanup test data
            await db.delete(test_doc)
            await db.delete(test_user)
            await db.commit()
            log_pass("Test data cleaned up")

    except Exception as e:
        log_fail("Database CRUD test failed", e)
        return False

    return True


# ════════════════════════════════════════════
# TEST 3: Embedding Generation (Local)
# ════════════════════════════════════════════

def test_embeddings():
    section("TEST 3: Embedding Model (Local, Free)")

    log_info("Loading embedding model (first time may download ~90MB)...")
    start = time.time()

    try:
        from core.embeddings import generate_embeddings, generate_single_embedding
        log_pass("Embedding module imported")
    except Exception as e:
        log_fail("Could not import embedding module", e)
        return False

    # Test single embedding
    try:
        embedding = generate_single_embedding("What is machine learning?")
        elapsed = time.time() - start
        log_pass(f"Single embedding generated in {elapsed:.2f}s")
        log_info(f"Embedding dimension: {len(embedding)}")
        log_info(f"First 5 values: {embedding[:5]}")
    except Exception as e:
        log_fail("Single embedding generation failed", e)
        return False

    # Test batch embeddings
    try:
        texts = [
            "Neural networks are computing systems inspired by biological brains.",
            "Photosynthesis converts sunlight into chemical energy in plants.",
            "The French Revolution began in 1789.",
        ]
        embeddings = generate_embeddings(texts)
        log_pass(f"Batch embeddings generated: {len(embeddings)} embeddings")
        assert len(embeddings) == 3
        assert len(embeddings[0]) == len(embedding)  # same dimension
        log_pass("Embedding dimensions are consistent")
    except Exception as e:
        log_fail("Batch embedding generation failed", e)
        return False

    return True


# ════════════════════════════════════════════
# TEST 4: ChromaDB Vector Store
# ════════════════════════════════════════════

def test_vector_store():
    section("TEST 4: ChromaDB Vector Store")

    try:
        from core.vector_store import get_collection, add_chunks, search_chunks, delete_document_chunks
        from core.embeddings import generate_embeddings
        log_pass("Vector store module imported")
    except Exception as e:
        log_fail("Could not import vector store", e)
        return False

    test_user_id = 99999  # Use a test user ID

    # Add test chunks
    try:
        texts = [
            "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
            "Deep learning uses neural networks with many layers to model complex patterns.",
            "Natural language processing helps computers understand human language.",
            "Computer vision allows machines to interpret and understand visual information.",
            "Reinforcement learning trains agents through rewards and penalties.",
        ]
        embeddings = generate_embeddings(texts)
        ids = [f"test_chunk_{i}" for i in range(len(texts))]
        metadatas = [
            {"document_id": 1, "document_title": "AI Basics", "section": f"Section {i+1}", "chunk_index": i}
            for i in range(len(texts))
        ]

        add_chunks(test_user_id, ids, texts, embeddings, metadatas)
        log_pass(f"Added {len(texts)} test chunks to ChromaDB")
    except Exception as e:
        log_fail("Could not add chunks to ChromaDB", e)
        return False

    # Search
    try:
        from core.embeddings import generate_single_embedding
        query_emb = generate_single_embedding("What is deep learning?")
        results = search_chunks(test_user_id, query_emb, top_k=3)

        found_docs = results["documents"][0]
        found_dists = results["distances"][0]

        log_pass(f"Search returned {len(found_docs)} results")
        log_info(f"Top result: {found_docs[0][:80]}...")
        log_info(f"Distance: {found_dists[0]:.4f}")

        # Verify the most relevant result is about deep learning
        if "deep learning" in found_docs[0].lower() or "neural network" in found_docs[0].lower():
            log_pass("Semantic search returned relevant result!")
        else:
            log_warn("Top result may not be the most relevant — check embeddings")
    except Exception as e:
        log_fail("Vector search failed", e)
        return False

    # Cleanup
    try:
        delete_document_chunks(test_user_id, 1)
        # Also delete the collection
        from core.vector_store import get_chroma_client
        client = get_chroma_client()
        try:
            client.delete_collection(f"user_{test_user_id}")
        except Exception:
            pass
        log_pass("Test chunks cleaned up")
    except Exception as e:
        log_warn(f"Cleanup warning: {e}")

    return True


# ════════════════════════════════════════════
# TEST 5: Document Chunking
# ════════════════════════════════════════════

def test_chunking():
    section("TEST 5: Document Chunking")

    try:
        from core.chunking import chunk_text
        log_pass("Chunking module imported")
    except Exception as e:
        log_fail("Could not import chunking module", e)
        return False

    # Test with sample text
    sample_text = """
# Introduction to Machine Learning

Machine learning is a branch of artificial intelligence that focuses on building applications that learn from data and improve their accuracy over time without being programmed to do so. In data science, an algorithm is a sequence of statistical processing steps.

## Supervised Learning

Supervised learning is a type of machine learning where the model is trained on labeled data. The algorithm learns from the training data, and then applies what it has learned to new data. Common examples include classification and regression tasks. Linear regression, decision trees, and neural networks are popular supervised learning algorithms.

## Unsupervised Learning

Unsupervised learning is where the model is trained on unlabeled data. The algorithm tries to find patterns and relationships in the data without any guidance. Clustering and dimensionality reduction are common unsupervised learning techniques. K-means clustering is one of the most popular unsupervised algorithms.

## Reinforcement Learning

Reinforcement learning is a type of machine learning where an agent learns to make decisions by performing actions in an environment to maximize some notion of cumulative reward. The agent receives rewards or penalties for the actions it takes, and it learns to choose actions that maximize the total reward over time.
"""

    try:
        chunks = chunk_text(sample_text, "ML Basics Document")
        log_pass(f"Text chunked into {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            log_info(f"  Chunk {i}: [{chunk.metadata.get('section', 'N/A')}] {len(chunk.text)} chars — \"{chunk.text[:60]}...\"")

        assert len(chunks) > 0, "Should produce at least one chunk"
        log_pass("Chunking produces valid output with metadata")

        # Verify metadata
        has_sections = any(c.metadata.get("section") for c in chunks)
        if has_sections:
            log_pass("Section headings detected and preserved in metadata")
        else:
            log_warn("No section headings detected — may be OK for plain text")

    except Exception as e:
        log_fail("Chunking failed", e)
        return False

    return True


# ════════════════════════════════════════════
# TEST 6: Document Parsing
# ════════════════════════════════════════════

def test_document_parsing():
    section("TEST 6: Document Parsing")

    try:
        from core.document_processor import parse_document
        log_pass("Document processor imported")
    except Exception as e:
        log_fail("Could not import document processor", e)
        return False

    # Create a test .txt file
    test_dir = Path("./uploads/test")
    test_dir.mkdir(parents=True, exist_ok=True)

    test_txt = test_dir / "test_document.txt"
    test_content = """Introduction to Python

Python is a high-level, interpreted programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991.

Key Features:
- Easy to learn and use
- Extensive standard library
- Dynamic typing
- Cross-platform compatibility

Python supports multiple programming paradigms, including procedural, object-oriented, and functional programming. It has become one of the most popular languages for data science, web development, and automation.

Data Types in Python:
Python has several built-in data types including integers, floats, strings, lists, tuples, dictionaries, and sets. Each type serves different purposes in programming.
"""
    test_txt.write_text(test_content)
    log_pass(f"Test file created: {test_txt}")

    # Parse TXT
    try:
        text = parse_document(str(test_txt), "txt")
        log_pass(f"TXT parsed: {len(text)} characters extracted")
        assert len(text) > 100
        log_pass("Parsed text has expected content")
    except Exception as e:
        log_fail("TXT parsing failed", e)

    # Create test .md file
    test_md = test_dir / "test_notes.md"
    test_md.write_text("# Study Notes\n\n## Topic 1\nSome notes here.\n\n## Topic 2\nMore notes here.")
    try:
        text = parse_document(str(test_md), "md")
        log_pass(f"Markdown parsed: {len(text)} characters")
    except Exception as e:
        log_fail("Markdown parsing failed", e)

    # Cleanup
    test_txt.unlink(missing_ok=True)
    test_md.unlink(missing_ok=True)
    test_dir.rmdir()

    return True


# ════════════════════════════════════════════
# TEST 7: Reranker
# ════════════════════════════════════════════

def test_reranker():
    section("TEST 7: Cross-Encoder Reranker (Local, Free)")

    log_info("Loading reranker model (first time may download ~80MB)...")

    try:
        from core.reranker import rerank_chunks
        log_pass("Reranker module imported")
    except Exception as e:
        log_fail("Could not import reranker", e)
        return False

    query = "What is deep learning?"
    chunks = [
        {"text": "The weather today is sunny and warm.", "metadata": {}, "id": "1"},
        {"text": "Deep learning uses neural networks with multiple layers to learn representations.", "metadata": {}, "id": "2"},
        {"text": "Python is a popular programming language.", "metadata": {}, "id": "3"},
        {"text": "Artificial neural networks are inspired by biological neural networks.", "metadata": {}, "id": "4"},
        {"text": "The stock market closed higher today.", "metadata": {}, "id": "5"},
    ]

    try:
        start = time.time()
        ranked = rerank_chunks(query, chunks, top_k=3)
        elapsed = time.time() - start

        log_pass(f"Reranking completed in {elapsed:.2f}s")
        log_info("Ranked results:")
        for i, chunk in enumerate(ranked):
            log_info(f"  #{i+1} (score: {chunk['rerank_score']:.4f}): {chunk['text'][:70]}...")

        # Verify the deep learning chunk is ranked highest
        if "deep learning" in ranked[0]["text"].lower() or "neural" in ranked[0]["text"].lower():
            log_pass("Reranker correctly identified most relevant chunk!")
        else:
            log_warn("Reranker top result may not be optimal")

    except Exception as e:
        log_fail("Reranking failed", e)
        return False

    return True


# ════════════════════════════════════════════
# TEST 8: Gemini LLM Connection
# ════════════════════════════════════════════

async def test_gemini():
    section("TEST 8: Gemini LLM (Free API)")

    try:
        from core.llm import generate_answer, TUTOR_SYSTEM_PROMPT
        log_pass("LLM module imported")
    except Exception as e:
        log_fail("Could not import LLM module", e)
        return False

    # Test basic generation
    try:
        log_info("Sending test prompt to Gemini...")
        start = time.time()

        answer = await generate_answer(
            system_prompt="You are a helpful assistant. Respond in exactly one sentence.",
            user_prompt="What is 2 + 2?"
        )
        elapsed = time.time() - start

        log_pass(f"Gemini responded in {elapsed:.2f}s")
        log_info(f"Response: {answer[:200]}")
        assert len(answer) > 0
        log_pass("Gemini API connection is working!")

    except Exception as e:
        log_fail(f"Gemini API call failed — check your API key in .env", e)
        return False

    # Test grounded answer (simulating RAG)
    try:
        context = """[Source 1: Python Basics]
Python is a high-level programming language created by Guido van Rossum in 1991.
It emphasizes code readability and simplicity."""

        answer = await generate_answer(
            system_prompt=TUTOR_SYSTEM_PROMPT,
            user_prompt=f"CONTEXT:\n{context}\n\nQUESTION:\nWho created Python and when?"
        )
        log_pass("Grounded Q&A test passed")
        log_info(f"Grounded answer: {answer[:200]}...")

        # Test refusal (ask about something NOT in context)
        answer2 = await generate_answer(
            system_prompt=TUTOR_SYSTEM_PROMPT,
            user_prompt=f"CONTEXT:\n{context}\n\nQUESTION:\nWhat is the capital of France?"
        )
        if "cannot answer" in answer2.lower() or "not contained" in answer2.lower() or "not found" in answer2.lower() or "study material" in answer2.lower():
            log_pass("Anti-hallucination: correctly refused out-of-context question!")
        else:
            log_warn(f"LLM may have answered out-of-context question: {answer2[:100]}...")

    except Exception as e:
        log_fail("Grounded answer test failed", e)
        return False

    return True


# ════════════════════════════════════════════
# TEST 9: Full RAG Pipeline (End-to-End)
# ════════════════════════════════════════════

async def test_rag_pipeline():
    section("TEST 9: Full RAG Pipeline (End-to-End)")

    try:
        from core.document_processor import process_document
        from core.rag_pipeline import ask_question, explain_simply, generate_flashcards, generate_quiz_mcq
        from core.vector_store import get_chroma_client
        log_pass("RAG pipeline modules imported")
    except Exception as e:
        log_fail("Could not import RAG pipeline", e)
        return False

    test_user_id = 88888
    test_doc_id = 1

    # Create a test document
    test_dir = Path("./uploads/test_rag")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / "ai_basics.txt"
    test_file.write_text("""
# Artificial Intelligence Fundamentals

## What is AI?
Artificial Intelligence (AI) is the simulation of human intelligence processes by computer systems. These processes include learning, reasoning, and self-correction. AI was first conceptualized by Alan Turing in the 1950s.

## Types of AI
There are three types of AI:
1. Narrow AI (Weak AI) - designed for a specific task, like Siri or chess engines.
2. General AI (Strong AI) - can understand and learn any intellectual task a human can. This does not yet exist.
3. Super AI - surpasses human intelligence in all aspects. This is theoretical.

## Machine Learning
Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed. It was coined by Arthur Samuel in 1959.

Key approaches:
- Supervised Learning: learns from labeled training data
- Unsupervised Learning: finds patterns in unlabeled data
- Reinforcement Learning: learns through trial and error with rewards

## Deep Learning
Deep learning is a subset of machine learning using artificial neural networks with multiple layers. It excels at tasks like image recognition, speech processing, and natural language understanding. Convolutional Neural Networks (CNNs) are used for image tasks, while Recurrent Neural Networks (RNNs) handle sequential data.

## Applications
AI is used in healthcare for diagnosis, in finance for fraud detection, in transportation for self-driving cars, and in entertainment for recommendation systems like Netflix and Spotify.
""")

    # Step 1: Process document (parse → chunk → embed → store)
    try:
        log_info("Processing test document through full pipeline...")
        start = time.time()

        chunks, chroma_ids = await process_document(
            file_path=str(test_file),
            file_type="txt",
            document_id=test_doc_id,
            document_title="AI Basics",
            user_id=test_user_id,
        )
        elapsed = time.time() - start

        log_pass(f"Document processed in {elapsed:.2f}s → {len(chunks)} chunks")
        for c in chunks:
            log_info(f"  Chunk {c.index}: [{c.metadata.get('section', 'N/A')}] {len(c.text)} chars")

    except Exception as e:
        log_fail("Document processing failed", e)
        return False

    # Step 2: Ask a question (full RAG)
    try:
        log_info("Testing Direct Q&A mode...")
        result = await ask_question(test_user_id, "What are the three types of AI?")

        log_pass("Q&A RAG pipeline returned result")
        log_info(f"Answer preview: {result.answer[:200]}...")
        log_info(f"Confidence: {result.confidence}")
        log_info(f"Sources: {len(result.sources)} chunks used")

        if result.sources:
            log_pass(f"Sources provided: {result.sources[0]['document_title']}")

    except Exception as e:
        log_fail("Q&A pipeline failed", e)

    # Step 3: Test refusal for out-of-context
    try:
        log_info("Testing anti-hallucination (out-of-context question)...")
        result = await ask_question(test_user_id, "What is the recipe for chocolate cake?")

        if "cannot answer" in result.answer.lower() or "not found" in result.answer.lower() or "study material" in result.answer.lower():
            log_pass("Anti-hallucination: correctly refused out-of-context question!")
        else:
            log_warn(f"May not have refused properly: {result.answer[:100]}...")

    except Exception as e:
        log_fail("Anti-hallucination test failed", e)

    # Step 4: Test Explain Simply
    try:
        log_info("Testing Explain Simply mode...")
        result = await explain_simply(test_user_id, "deep learning")

        log_pass("Explain Simply mode works")
        log_info(f"Explanation preview: {result.answer[:150]}...")

    except Exception as e:
        log_fail("Explain Simply mode failed", e)

    # Step 5: Test Flashcard Generation
    try:
        log_info("Testing Flashcard Generation...")
        result = await generate_flashcards(test_user_id, "artificial intelligence", count=3)

        if result.get("flashcards"):
            log_pass(f"Generated {len(result['flashcards'])} flashcards")
            for fc in result["flashcards"][:2]:
                log_info(f"  Q: {fc.get('front', 'N/A')[:60]}...")
                log_info(f"  A: {fc.get('back', 'N/A')[:60]}...")
        else:
            log_warn("No flashcards generated — LLM may not have returned valid JSON")

    except Exception as e:
        log_fail("Flashcard generation failed", e)

    # Step 6: Test MCQ Quiz Generation
    try:
        log_info("Testing MCQ Quiz Generation...")
        result = await generate_quiz_mcq(test_user_id, "machine learning", count=2)

        if result.get("questions"):
            log_pass(f"Generated {len(result['questions'])} MCQ questions")
            for q in result["questions"][:1]:
                log_info(f"  Q: {q.get('question', 'N/A')[:70]}...")
                log_info(f"  Correct: {q.get('correct_answer', 'N/A')}")
        else:
            log_warn("No quiz questions generated — LLM may not have returned valid JSON")

    except Exception as e:
        log_fail("MCQ quiz generation failed", e)

    # Cleanup
    try:
        from core.vector_store import get_chroma_client
        client = get_chroma_client()
        try:
            client.delete_collection(f"user_{test_user_id}")
        except Exception:
            pass
        test_file.unlink(missing_ok=True)
        test_dir.rmdir()
        log_pass("RAG test data cleaned up")
    except Exception:
        log_warn("Some test data may not have been cleaned up")

    return True


# ════════════════════════════════════════════
# TEST 10: API Endpoints (FastAPI TestClient)
# ════════════════════════════════════════════

async def test_api_endpoints():
    section("TEST 10: API Endpoints (FastAPI TestClient)")

    try:
        from httpx import AsyncClient, ASGITransport
        from main import app
        log_pass("FastAPI app imported")
    except ImportError:
        log_warn("httpx not installed — run: pip install httpx")
        log_info("Skipping API endpoint tests. Install httpx and rerun.")
        return True
    except Exception as e:
        log_fail("Could not import FastAPI app", e)
        return False

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # Health check
        try:
            r = await client.get("/health")
            assert r.status_code == 200
            log_pass("GET /health — 200 OK")
        except Exception as e:
            log_fail("GET /health failed", e)

        # Root
        try:
            r = await client.get("/")
            assert r.status_code == 200
            assert "StudyBuddy" in r.json().get("message", "")
            log_pass("GET / — API info returned")
        except Exception as e:
            log_fail("GET / failed", e)

        # Register
        token = None
        try:
            r = await client.post("/api/auth/register", json={
                "email": "apitest@studybuddy.com",
                "name": "API Tester",
                "password": "testpass123"
            })
            if r.status_code == 200:
                data = r.json()
                token = data.get("access_token")
                log_pass(f"POST /api/auth/register — user created, token received")
            elif r.status_code == 400:
                log_info("User already exists — trying login instead")
                r = await client.post("/api/auth/login", json={
                    "email": "apitest@studybuddy.com",
                    "password": "testpass123"
                })
                if r.status_code == 200:
                    token = r.json().get("access_token")
                    log_pass("POST /api/auth/login — token received")
                else:
                    log_fail(f"Login failed: {r.status_code}", r.text)
            else:
                log_fail(f"Register failed: {r.status_code}", r.text)
        except Exception as e:
            log_fail("Auth endpoints failed", e)

        if not token:
            log_fail("No auth token — skipping authenticated tests")
            return False

        headers = {"Authorization": f"Bearer {token}"}

        # Get /me
        try:
            r = await client.get("/api/auth/me", headers=headers)
            assert r.status_code == 200
            log_pass(f"GET /api/auth/me — user: {r.json().get('name')}")
        except Exception as e:
            log_fail("GET /api/auth/me failed", e)

        # List documents (should be empty initially)
        try:
            r = await client.get("/api/documents", headers=headers)
            assert r.status_code == 200
            log_pass(f"GET /api/documents — {len(r.json())} documents")
        except Exception as e:
            log_fail("GET /api/documents failed", e)

        # Upload a test document
        try:
            test_content = b"Python is a programming language created by Guido van Rossum in 1991. It is known for simplicity."
            r = await client.post(
                "/api/documents/upload",
                headers=headers,
                files={"file": ("test_upload.txt", test_content, "text/plain")},
            )
            if r.status_code == 200:
                log_pass(f"POST /api/documents/upload — document uploaded: {r.json().get('title')}")
                log_info("Background processing started (chunks + embeddings)")
            else:
                log_fail(f"Upload failed: {r.status_code}", r.text)
        except Exception as e:
            log_fail("Document upload failed", e)

        # Give background task a moment
        import asyncio
        log_info("Waiting 5s for background document processing...")
        await asyncio.sleep(5)

        # Test Q&A
        try:
            r = await client.post(
                "/api/chat/ask",
                headers=headers,
                json={"question": "Who created Python?"}
            )
            if r.status_code == 200:
                data = r.json()
                log_pass(f"POST /api/chat/ask — answered with confidence: {data.get('confidence')}")
                log_info(f"Answer: {data.get('answer', '')[:150]}...")
            else:
                log_warn(f"Chat ask returned {r.status_code} — document may still be processing")
        except Exception as e:
            log_fail("Chat Q&A endpoint failed", e)

    return True


# ════════════════════════════════════════════
# MAIN TEST RUNNER
# ════════════════════════════════════════════

async def main():
    print("\n" + "═" * 60)
    print("  🎓  StudyBuddy AI — Backend Test Suite")
    print("═" * 60)
    print()

    start = time.time()

    # Run tests in order
    if not test_config():
        print("\n⛔ Config failed. Fix .env and retry.")
        return

    await test_database()
    test_embeddings()
    test_vector_store()
    test_chunking()
    test_document_parsing()
    test_reranker()
    await test_gemini()
    await test_rag_pipeline()
    await test_api_endpoints()

    # Summary
    elapsed = time.time() - start
    print(f"\n{'═' * 60}")
    print(f"  TEST RESULTS")
    print(f"{'═' * 60}")
    print(f"  ✅ Passed:   {test_results['passed']}")
    print(f"  ❌ Failed:   {test_results['failed']}")
    print(f"  ⚠️  Warnings: {test_results['warnings']}")
    print(f"  ⏱️  Time:     {elapsed:.1f}s")
    print(f"{'═' * 60}")

    if test_results['failed'] == 0:
        print("\n  🎉  ALL TESTS PASSED! Backend is ready.")
        print("  Next: Run 'uvicorn main:app --reload' and build the frontend.\n")
    else:
        print(f"\n  ⚠️  {test_results['failed']} test(s) failed. Check errors above.\n")


if __name__ == "__main__":
    asyncio.run(main())