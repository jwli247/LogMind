from core.embeddings import get_embedding_model


def main() -> None:
    embeddings = get_embedding_model()
    vector = embeddings.embed_query("LogMind RAG embedding check")

    print("LangChain Embeddings 调用成功。")
    print(f"向量维度：{len(vector)}")
    print(f"前 5 个向量值：{vector[:5]}")


if __name__ == "__main__":
    main()