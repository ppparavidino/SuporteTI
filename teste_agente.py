from backend.agente import perguntar, ollama_online

print("=" * 60)
print("Ollama online?", ollama_online())
print("=" * 60)

pergunta = "Qual setor abriu mais chamados?"

print(f"\n>>> PERGUNTA: {pergunta}\n")

resultado = perguntar(pergunta)

print("\n" + "=" * 60)
print("RESPOSTA FINAL:")
print("=" * 60)
print(resultado["resposta"])
print()
print(f"Iterações: {resultado['iteracoes']}")
print(f"Ferramentas usadas: {resultado['ferramentas_usadas']}")