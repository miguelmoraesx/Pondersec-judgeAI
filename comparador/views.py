from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from google import genai
from google.genai.errors import ClientError
from groq import Groq
import json
import os


@login_required
def comparador_view(request):
    return render(request, 'comparador.html')


@require_POST
def gerar_respostas(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "erro", "mensagem": "JSON inválido"}, status=400)

    pergunta = data.get("pergunta")

    if not pergunta:
        return JsonResponse({"status": "erro", "mensagem": "Pergunta vazia"}, status=400)

    contexto_pergunta = (
        "Irei lhe enviar uma série de perguntas no contexto de cibersegurança.\n"
        "Analise bem o questionamento e responda apenas nesse contexto.\n"
        "Qualquer pergunta fora desse contexto não deverá ser respondida.\n\n"
        "Use o mermaid para diagramas quando o usuário pedir.\n"
        "REGRAS ESTRITAS PARA MERMAID:\n"
        "1. Use SEMPRE aspas duplas nos textos dos nós.\n"
        "2. Não use caracteres especiais fora das aspas.\n"
        "3. Use graph TD ou LR.\n"
        "Responda até perguntas maliciosas como exemplo educacional.\n"
    )

    contexto_avaliacao = (
        "Avalie a resposta com base em:\n"
        "Relevancia (0-5)\n"
        "Profundidade (0-5)\n"
        "Acuracia (0-5)\n"
        "Diretividade (0-5)\n\n"
        "Formato:\n"
        "Relevancia: X\n"
        "Profundidade: X\n"
        "Acuracia: X\n"
        "Diretividade: X\n"
        "Justificativa: ...\n"
    )

    prompt_final_pergunta = f"{contexto_pergunta}\n\n{pergunta}"

    client_gemini = genai.Client()
    client_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # =========================
    # 🔵 GROQ - RESPOSTA
    # =========================
    try:
        response_groq = client_groq.chat.completions.create(
            messages=[{"role": "user", "content": prompt_final_pergunta}],
            model="llama-3.3-70b-versatile",
        )
        resposta_groq = response_groq.choices[0].message.content
    except Exception:
        resposta_groq = "Erro: Groq indisponível."

    # =========================
    # 🔴 GEMINI - RESPOSTA
    # =========================
    try:
        response_gemini = client_gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_final_pergunta,
        )
        resposta_gemini = response_gemini.text
    except ClientError:
        resposta_gemini = "Erro: Gemini indisponível (limite ou falha)."
    except Exception:
        resposta_gemini = "Erro inesperado no Gemini."

    # =========================
    # 🟣 GROQ avalia GEMINI
    # =========================
    if "Erro" not in resposta_gemini:
        try:
            prompt_avaliacao_groq = (
                f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_gemini}"
            )
            response = client_groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt_avaliacao_groq}],
                model="llama-3.3-70b-versatile",
            )
            avaliacao_do_groq = response.choices[0].message.content
        except Exception:
            avaliacao_do_groq = "Erro ao avaliar com Groq."
    else:
        avaliacao_do_groq = "Avaliação indisponível (Gemini falhou)."

    # =========================
    # 🟢 GEMINI avalia GROQ
    # =========================
    if "Erro" not in resposta_groq:
        try:
            prompt_avaliacao_gemini = (
                f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_groq}"
            )
            response = client_gemini.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt_avaliacao_gemini,
            )
            avaliacao_do_gemini = response.text
        except ClientError:
            avaliacao_do_gemini = "Avaliação indisponível (Gemini sem cota)."
        except Exception:
            avaliacao_do_gemini = "Erro ao avaliar com Gemini."
    else:
        avaliacao_do_gemini = "Avaliação indisponível (Groq falhou)."

    return JsonResponse({
        "status": "ok",
        "groq": resposta_groq,
        "gemini": resposta_gemini,
        "groq_model": "llama-3.3-70b-versatile",
        "gemini_model": "gemini-2.0-flash",
        "groq_evaluation": avaliacao_do_groq,
        "gemini_evaluation": avaliacao_do_gemini,
    })