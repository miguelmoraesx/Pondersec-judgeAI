from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from google import genai
from google.genai.errors import ClientError
from groq import Groq
from openai import OpenAI

import json
import os


@login_required
def comparador_view(request):
    return render(request, 'comparador.html')


@login_required
@require_POST
def gerar_respostas(request):
    # =========================
    # PARSE REQUEST
    # =========================
    try:
        data = json.loads(request.body)

        api_keys = data.get("api_keys", {})

    except json.JSONDecodeError:
        return JsonResponse({"status": "erro", "mensagem": "JSON inválido"}, status=400)

    pergunta = data.get("pergunta")

    if not pergunta:
        return JsonResponse({"status": "erro", "mensagem": "Pergunta vazia"}, status=400)

    # =========================
    # CONTEXTOS
    # =========================
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

    prompt_final = f"{contexto_pergunta}\n\n{pergunta}"

    # =========================
    # CLIENTS
    # =========================
    client_groq = None
    client_gemini = None
    client_chatgpt = None
    client_deepseek = None

    # GROQ
    if api_keys.get("groq"):
        client_groq = Groq(api_key=api_keys["groq"])

    # GEMINI
    if api_keys.get("gemini"):
        client_gemini = genai.Client(api_key=api_keys["gemini"])

    # CHATGPT
    if api_keys.get("openai"):
        client_chatgpt = OpenAI(api_key=api_keys["openai"])

    # DEEPSEEK
    if api_keys.get("deepseek"):
        client_deepseek = OpenAI(
            api_key=api_keys["deepseek"],
            base_url="https://api.deepseek.com"
        )

    # MODELS
    groq_model = "llama-3.3-70b-versatile"
    gemini_model = "gemini-2.5-flash"
    chatgpt_model = "gpt-5.5"
    deepseek_model = "deepseek-v4-pro"

    # =========================
    # GROQ
    # =========================
    groq_ok = False
    resposta_groq = ""

    try:
        response = client_groq.chat.completions.create(
            messages=[{"role": "user", "content": prompt_final}],
            model=groq_model,
        )
        resposta_groq = response.choices[0].message.content
        groq_model = response.model
        groq_ok = True
    except Exception as e:
        resposta_groq = f"Erro: Groq indisponível ({type(e).__name__})"

    # =========================
    # GEMINI
    # =========================
    gemini_ok = False
    resposta_gemini = ""

    try:
        response = client_gemini.models.generate_content(
            model=gemini_model,
            contents=prompt_final,
        )
        resposta_gemini = response.text
        gemini_ok = True
    except ClientError as e:
        resposta_gemini = f"Erro Gemini ({type(e).__name__})"
    except Exception as e:
        resposta_gemini = f"Erro inesperado Gemini ({type(e).__name__})"

    # =========================
    # CHATGPT
    # =========================
    chatgpt_ok = False
    resposta_chatgpt = ""

    try:
        response = client_chatgpt.responses.create(
            model=chatgpt_model,
            input=prompt_final
        )
        resposta_chatgpt = response.output_text
        chatgpt_ok = True
    except Exception as e:
        resposta_chatgpt = f"Erro ChatGPT ({type(e).__name__})"

    # =========================
    # DEEPSEEK
    # =========================
    deepseek_ok = False
    resposta_deepseek = ""

    try:
        response = client_deepseek.chat.completions.create(
            model=deepseek_model,
            messages=[{"role": "user", "content": prompt_final}],
            stream=False,
        )
        resposta_deepseek = response.choices[0].message.content
        deepseek_ok = True
    except Exception as e:
        resposta_deepseek = f"Erro DeepSeek ({type(e).__name__})"

    # =========================
    # AVALIAÇÕES CRUZADAS
    # =========================

    # -------- GROQ avalia --------
    avaliacoes_groq = {}

    # Groq → Gemini
    if gemini_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_gemini}"
            response = client_groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=groq_model,
            )
            avaliacoes_groq["gemini"] = response.choices[0].message.content
        except Exception:
            avaliacoes_groq["gemini"] = "Erro avaliação Groq"
    else:
        avaliacoes_groq["gemini"] = "Indisponível"

    # Groq → GPT
    if chatgpt_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_chatgpt}"
            response = client_groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=groq_model,
            )
            avaliacoes_groq["gpt"] = response.choices[0].message.content
        except Exception:
            avaliacoes_groq["gpt"] = "Erro avaliação Groq"
    else:
        avaliacoes_groq["gpt"] = "Indisponível"

    # Groq → DeepSeek
    if deepseek_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_deepseek}"
            response = client_groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=groq_model,
            )
            avaliacoes_groq["deepseek"] = response.choices[0].message.content
        except Exception:
            avaliacoes_groq["deepseek"] = "Erro avaliação Groq"
    else:
        avaliacoes_groq["deepseek"] = "Indisponível"


    # -------- GEMINI avalia --------
    avaliacoes_gemini = {}

    # Gemini → Groq
    if groq_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_groq}"
            response = client_gemini.models.generate_content(
                model=gemini_model,
                contents=prompt,
            )
            avaliacoes_gemini["groq"] = response.text
        except Exception:
            avaliacoes_gemini["groq"] = "Erro avaliação Gemini"
    else:
        avaliacoes_gemini["groq"] = "Indisponível"

    # Gemini → GPT
    if chatgpt_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_chatgpt}"
            response = client_gemini.models.generate_content(
                model=gemini_model,
                contents=prompt,
            )
            avaliacoes_gemini["gpt"] = response.text
        except Exception:
            avaliacoes_gemini["gpt"] = "Erro avaliação Gemini"
    else:
        avaliacoes_gemini["gpt"] = "Indisponível"

    # Gemini → DeepSeek
    if deepseek_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_deepseek}"
            response = client_gemini.models.generate_content(
                model=gemini_model,
                contents=prompt,
            )
            avaliacoes_gemini["deepseek"] = response.text
        except Exception:
            avaliacoes_gemini["deepseek"] = "Erro avaliação Gemini"
    else:
        avaliacoes_gemini["deepseek"] = "Indisponível"


    # -------- GPT avalia --------
    avaliacoes_gpt = {}

    # GPT → Groq
    if groq_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_groq}"
            response = client_chatgpt.responses.create(
                model=chatgpt_model,
                input=prompt
            )
            avaliacoes_gpt["groq"] = response.output_text
        except Exception:
            avaliacoes_gpt["groq"] = "Erro avaliação ChatGPT"
    else:
        avaliacoes_gpt["groq"] = "Indisponível"

    # GPT → Gemini
    if gemini_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_gemini}"
            response = client_chatgpt.responses.create(
                model=chatgpt_model,
                input=prompt
            )
            avaliacoes_gpt["gemini"] = response.output_text
        except Exception:
            avaliacoes_gpt["gemini"] = "Erro avaliação ChatGPT"
    else:
        avaliacoes_gpt["gemini"] = "Indisponível"

    # GPT → DeepSeek
    if deepseek_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_deepseek}"
            response = client_chatgpt.responses.create(
                model=chatgpt_model,
                input=prompt
            )
            avaliacoes_gpt["deepseek"] = response.output_text
        except Exception:
            avaliacoes_gpt["deepseek"] = "Erro avaliação ChatGPT"
    else:
        avaliacoes_gpt["deepseek"] = "Indisponível"


    # -------- DEEPSEEK avalia --------
    avaliacoes_deepseek = {}

    # DeepSeek → Groq
    if groq_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_groq}"
            response = client_deepseek.chat.completions.create(
                model=deepseek_model,
                messages=[{"role": "user", "content": prompt}],
            )
            avaliacoes_deepseek["groq"] = response.choices[0].message.content
        except Exception:
            avaliacoes_deepseek["groq"] = "Erro avaliação DeepSeek"
    else:
        avaliacoes_deepseek["groq"] = "Indisponível"

    # DeepSeek → Gemini
    if gemini_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_gemini}"
            response = client_deepseek.chat.completions.create(
                model=deepseek_model,
                messages=[{"role": "user", "content": prompt}],
            )
            avaliacoes_deepseek["gemini"] = response.choices[0].message.content
        except Exception:
            avaliacoes_deepseek["gemini"] = "Erro avaliação DeepSeek"
    else:
        avaliacoes_deepseek["gemini"] = "Indisponível"

    # DeepSeek → GPT
    if chatgpt_ok:
        try:
            prompt = f"{contexto_avaliacao}\n\nPERGUNTA: {pergunta}\n\nRESPOSTA:\n{resposta_chatgpt}"
            response = client_deepseek.chat.completions.create(
                model=deepseek_model,
                messages=[{"role": "user", "content": prompt}],
            )
            avaliacoes_deepseek["gpt"] = response.choices[0].message.content
        except Exception:
            avaliacoes_deepseek["gpt"] = "Erro avaliação DeepSeek"
    else:
        avaliacoes_deepseek["gpt"] = "Indisponível"

    # =========================
    # RESPONSE FINAL
    # =========================
    return JsonResponse({
        "status": "ok",

        "groq_ok": groq_ok,
        "gemini_ok": gemini_ok,
        "chatgpt_ok": chatgpt_ok,
        "deepseek_ok": deepseek_ok,

        "groq": resposta_groq,
        "gemini": resposta_gemini,
        "chatgpt": resposta_chatgpt,
        "deepseek": resposta_deepseek,

        "groq_model": groq_model,
        "gemini_model": gemini_model,
        "chatgpt_model": chatgpt_model,
        "deepseek_model": deepseek_model,

        "evaluations": {
        "groq": avaliacoes_groq,
        "gemini": avaliacoes_gemini,
        "gpt": avaliacoes_gpt,
        "deepseek": avaliacoes_deepseek,    
        }
    })