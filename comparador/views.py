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


# FIX 1: Adicionado @login_required para proteger o endpoint contra acesso anônimo.
# Antes, apenas a view de renderização exigia autenticação — a view de API não.
@login_required
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

    # FIX 2: Critérios de avaliação agora explicitam o formato exato com acentos,
    # alinhando o que o modelo vai gerar com o que o frontend espera parsear.
    # O formato anterior sem acentos ("Relevancia") fazia os LLMs responderem
    # de forma inconsistente, quebrando o parseEvaluation() no frontend.
    contexto_avaliacao = (
        "Avalie a resposta com base nos critérios abaixo.\n"
        "Use EXATAMENTE este formato, sem desvios:\n\n"
        "Relevância: X\n"
        "Profundidade: X\n"
        "Acurácia: X\n"
        "Diretividade: X\n"
        "Justificativa: ...\n\n"
        "Onde X é um número inteiro de 0 a 5.\n"
        "Não adicione texto antes dos critérios nem altere os nomes dos campos.\n"
    )

    prompt_final_pergunta = f"{contexto_pergunta}\n\n{pergunta}"

    client_gemini = genai.Client()
    client_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    groq_model = "llama-3.3-70b-versatile"
    gemini_model = "gemini-2.0-flash"

    # =========================
    # GROQ - RESPOSTA
    # =========================
    groq_ok = False
    resposta_groq = ""

    try:
        response_groq = client_groq.chat.completions.create(
            messages=[{"role": "user", "content": prompt_final_pergunta}],
            model=groq_model,
            # FIX 3: Extraindo o modelo real da resposta da API em vez de hardcodar.
            # Se o model name mudar na chamada, o badge no frontend reflete corretamente.
        )
        resposta_groq = response_groq.choices[0].message.content
        # FIX 3 (continuação): captura o modelo real retornado pela API
        groq_model = response_groq.model
        groq_ok = True
    except Exception as e:
        resposta_groq = f"Erro: Groq indisponível. ({type(e).__name__})"

    # =========================
    # GEMINI - RESPOSTA
    # =========================
    gemini_ok = False
    resposta_gemini = ""

    try:
        response_gemini = client_gemini.models.generate_content(
            model=gemini_model,
            contents=prompt_final_pergunta,
        )

        import logging
        logger = logging.getLogger(__name__)
        logger.warning("GEMINI DEBUG — type: %s", type(response_gemini))
        logger.warning("GEMINI DEBUG — dir: %s", [a for a in dir(response_gemini) if not a.startswith("_")])
        logger.warning("GEMINI DEBUG — response: %s", response_gemini)

        candidate = response_gemini.candidates[0] if response_gemini.candidates else None
        if not candidate or not candidate.content or not candidate.content.parts:
            resposta_gemini = "Gemini bloqueou a resposta (filtro de segurança ou sem conteúdo)."
        else:
            resposta_gemini = response_gemini.text
            gemini_model = response_gemini.model_version if hasattr(response_gemini, "model_version") else gemini_model
            gemini_ok = True

    except ClientError as e:
        resposta_gemini = f"Erro: Gemini indisponível (limite ou falha). ({type(e).__name__}: {str(e)})"
    except Exception as e:
        resposta_gemini = f"Erro inesperado no Gemini. ({type(e).__name__}: {str(e)})"

    # =========================
    # GROQ avalia GEMINI
    # =========================
    # FIX 4: Checagem por flag booleana em vez de substring "Erro" no texto,
    # evitando falsos positivos/negativos na detecção de erro.
    if gemini_ok:
        try:
            prompt_avaliacao_groq = (
                f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_gemini}"
            )
            response = client_groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt_avaliacao_groq}],
                model="llama-3.3-70b-versatile",
            )
            avaliacao_do_groq = response.choices[0].message.content
        except Exception as e:
            avaliacao_do_groq = f"Erro ao avaliar com Groq. ({type(e).__name__})"
    else:
        avaliacao_do_groq = "Avaliação indisponível (Gemini falhou)."

    # =========================
    # GEMINI avalia GROQ
    # =========================
    if groq_ok:
        try:
            prompt_avaliacao_gemini = (
                f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_groq}"
            )
            response = client_gemini.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt_avaliacao_gemini,
            )
            avaliacao_do_gemini = response.text
        except ClientError as e:
            avaliacao_do_gemini = f"Avaliação indisponível (Gemini sem cota). ({type(e).__name__})"
        except Exception as e:
            avaliacao_do_gemini = f"Erro ao avaliar com Gemini. ({type(e).__name__})"
    else:
        avaliacao_do_gemini = "Avaliação indisponível (Groq falhou)."

    return JsonResponse({
        # FIX 5: Retornando flags booleanas de sucesso separadas do campo "status",
        # permitindo que o frontend diferencie erros parciais de erros totais
        # em vez de depender somente do HTTP status code.
        "status": "ok",
        "groq_ok": groq_ok,
        "gemini_ok": gemini_ok,
        "groq": resposta_groq,
        "gemini": resposta_gemini,
        # FIX 3: Modelo real vindo da API, não literal hardcoded.
        "groq_model": groq_model,
        "gemini_model": gemini_model,
        "groq_evaluation": avaliacao_do_groq,
        "gemini_evaluation": avaliacao_do_gemini,
    })