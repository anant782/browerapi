from flask import Flask, request, jsonify
from auto_ai_server import KnowledgeBase, SearXNGClient

app = Flask(__name__)

kb = KnowledgeBase()
client = SearXNGClient("https://searx.be")  # change if self-hosted

@app.route("/query")
def query_ai():
    q = request.args.get("q")
    if not q:
        return jsonify({"error": "No query"}), 400

    if kb.has_full_information(q):
        ans, trust = kb.retrieve(q)
        return jsonify({"answer": ans, "source": "knowledge", "trust": trust})

    # fetch from SearXNG
    results = client.search(q)
    if not results:
        return jsonify({"answer": None, "source": "none"})

    best = results[0]
    content = best['content'] or best['title']
    kb.store(q, content, trust=0.8)
    kb.save()

    return jsonify({"answer": content, "source": best['title'], "trust": 0.8})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
