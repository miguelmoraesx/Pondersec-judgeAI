# 🔐 PonderSEC JudgeAI

Plataforma para **avaliação automática de Large Language Models (LLMs) em tarefas de cibersegurança**, utilizando **outras IAs como juízas**.

No **PonderSEC JudgeAI**, uma resposta gerada por um modelo não é avaliada diretamente por humanos, mas por **outros modelos de linguagem**, permitindo um processo de **avaliação cruzada automatizada**, escalável e reprodutível.

Por exemplo:

- **Gemini** responde uma questão
- **ChatGPT** e **DeepSeek** avaliam essa resposta
- o sistema registra notas, justificativas e comparações entre os modelos

Este projeto é uma evolução conceitual do **PonderSEC**, sendo desenvolvido no contexto de **Iniciação Científica (PIBITI/CNPq)** na **Universidade Federal do Amazonas (UFAM)**.

---

# 🎯 Objetivo

O **PonderSEC JudgeAI** busca fornecer um ambiente para:

- testar **LLMs em cenários de cibersegurança**
- gerar respostas automaticamente a partir de múltiplos modelos
- realizar **avaliação cruzada entre IAs**
- analisar a qualidade das respostas com base em critérios definidos
- automatizar experimentos acadêmicos com maior escalabilidade
- comparar modelos tanto como **respondentes** quanto como **avaliadores**

---

# 🧠 Ideia Central

O fluxo do sistema segue a lógica:

```text
Pergunta → LLM respondente → LLMs avaliadoras → notas e justificativas
```

#### 👥 Autores * **Gabriel Assis** * **Miguel Moraes** * **Luiz Barbosa**

---
